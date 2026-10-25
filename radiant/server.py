import json
import mimetypes
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from string import Template
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlparse, parse_qs

BASE_DIR: Path = Path(__file__).resolve().parent

STATIC_DIRS: list[Path] = [
    BASE_DIR / "static",
    BASE_DIR / "static" / "modules",
    Path(sys.path[0]),
]

TEMPLATES_DIR: Path = BASE_DIR / "templates"


DEFAULT_CONFIG: dict[str, Any] = {
    "domain": "",
    "brython_version": "latest",
    "debug_level": "0",
    "path": ["."],
    "mock_imports": [],
    "static": [],
}


def render_template(name: str, context: Dict[str, Any]) -> bytes:
    """
    Render an HTML template using string substitution.

    Parameters
    ----------
    name : str
        Template filename.
    context : dict
        Template variables.

    Returns
    -------
    bytes
        Rendered template encoded as UTF-8.
    """
    path = TEMPLATES_DIR / name
    template = Template(path.read_text(encoding="utf-8"))

    # Default missing keys to empty strings
    rendered = template.safe_substitute(defaultdict(str, context))
    return rendered.encode("utf-8")


def parse_query(path):
    """
    Normaliza el query string:
    - key=value      -> key: value
    - key=a&key=b    -> key: [a, b]
    """
    parsed = urlparse(path)
    raw = parse_qs(parsed.query, keep_blank_values=True)

    normalized = {}
    for key, values in raw.items():
        if len(values) == 1:
            normalized[key] = values[0]
        else:
            normalized[key] = values

    return normalized


class RequestHandler(BaseHTTPRequestHandler):
    """
    Minimal HTTP request handler with static file and template support.
    """

    server_version = "SimplePythonHTTP/1.0"

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return b""
        return self.rfile.read(length)

    def _get_post_data(self):
        content_type = self.headers.get("Content-Type", "")
        raw = self._read_body()

        if not raw:
            return None

        if "application/json" in content_type:
            import json

            return json.loads(raw)

        if "application/x-www-form-urlencoded" in content_type:
            from urllib.parse import parse_qs

            data = parse_qs(raw.decode())
            return {k: v[0] if len(v) == 1 else v for k, v in data.items()}

        return raw  # bytes crudos

    def _send(
        self,
        status: int = 200,
        body: Optional[bytes] = None,
        content_type: str = "text/plain",
    ) -> None:
        """
        Send an HTTP response.
        """
        self.send_response(status)
        self.send_header("Content-Type", content_type)

        if body is not None:
            self.send_header("Content-Length", str(len(body)))

        self.end_headers()

        if body is not None:
            self.wfile.write(body)

    def _serve_file(self, filepath: str) -> None:
        """
        Serve a static file.
        """
        if not os.path.isfile(filepath):
            self._send(404, b"Not Found")
            return

        content_type, _ = mimetypes.guess_type(filepath)
        content_type = content_type or "application/octet-stream"

        with open(filepath, "rb") as file:
            data = file.read()

        self._send(200, data, content_type)

    def do_GET(self) -> None:
        """
        Handle HTTP GET requests.
        """
        parsed = urlparse(self.path)
        query = parse_query(self.path)

        # ---------------- API ---------------- #

        if route := self.server.get_routes.get(parsed.path):
            self._send(**route(**query))
            return

        # ---------------- HTML ---------------- #

        if parsed.path == "/":
            html = render_template(
                "index.html",
                {
                    **DEFAULT_CONFIG,
                    **getattr(self.server, "config", {}),
                    "root_file": os.path.splitext(os.path.basename(sys.argv[0]))[0],
                    "call": "__init__",
                },
            )

            if self.server.generate_dist:

                dist_path = Path(self.server.generate_dist)
                if dist_path.exists():
                    shutil.rmtree(dist_path)
                dist_path.mkdir(parents=True, exist_ok=True)

                # Generate index.html
                (dist_path / "index.html").write_text(
                    html.decode("utf-8"), encoding="utf-8"
                )

                # Copy Brython package
                (dist_path / "brython").mkdir(parents=True, exist_ok=True)
                shutil.copytree(
                    BASE_DIR
                    / "static"
                    / "brython"
                    / f"Brython-{DEFAULT_CONFIG['brython_version']}",
                    dist_path
                    / "brython"
                    / f"Brython-{DEFAULT_CONFIG['brython_version']}",
                )

                # Generate main package
                app_dir = Path(sys.argv[0]).resolve().parent
                subprocess.run(
                    [
                        "brython-cli",
                        "make_package",
                        getattr(self.server, "config", {})["package"],
                    ],
                    cwd=app_dir,
                    capture_output=True,
                    text=True,
                )
                shutil.move(
                    app_dir
                    / f"{getattr(self.server, 'config', {})['package']}.brython.js",
                    dist_path,
                )

                # Copy Radiant package
                modules_dir = BASE_DIR / "static" / "modules"
                subprocess.run(
                    [
                        "brython-cli",
                        "make_package",
                        "radiant",
                    ],
                    cwd=modules_dir,
                    capture_output=True,
                    text=True,
                )
                shutil.move(
                    modules_dir / "radiant.brython.js",
                    dist_path,
                )

                # Copy Static paths

                static_dir = dist_path / "static"
                if static_dir.exists():
                    shutil.rmtree(static_dir)
                static_dir.mkdir(parents=True, exist_ok=True)

                for static in self.server.config.get("static", []):

                    for item in (app_dir / static).iterdir():
                        target = dist_path / "static" / item.name
                        if item.is_dir():
                            shutil.copytree(item, target, dirs_exist_ok=True)
                        else:
                            shutil.copy2(item, target)

            self._send(200, html, "text/html")
            return

        elif route := self.server.html_routes.get(parsed.path):

            html = render_template(
                "index.html",
                {
                    **DEFAULT_CONFIG,
                    **getattr(self.server, "config", {}),
                    "root_file": Path(sys.argv[0]).stem,
                    "call": route.__name__,
                },
            )
            self._send(200, html, "text/html")
            return

        # ---------------- STATIC FILES ---------------- #

        requested_path = parsed.path.lstrip("/")

        for static_dir in STATIC_DIRS + self.server.config.get("static", []):
            base = Path(static_dir).resolve()
            candidate = (base / requested_path).resolve()

            # Hardened directory traversal prevention
            if not candidate.is_relative_to(base):
                continue

            if candidate.is_file():
                self._serve_file(candidate)
                return

        self._send(404, b"Not Found")

    def do_POST(self) -> None:
        """
        Handle HTTP POST requests.
        """
        parsed = urlparse(self.path)

        try:
            data = self._get_post_data()
        except ValueError:
            self.send_error(400, "Invalid request body")
            return

        # ---------------- API ---------------- #

        if route := self.server.post_routes.get(parsed.path):
            self._send(**route(**data))
            return

        self._send(404, b"Not Found")
