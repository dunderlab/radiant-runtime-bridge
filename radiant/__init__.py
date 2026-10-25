from http.server import ThreadingHTTPServer
from typing import Any, Dict, Type, Callable, Optional

from radiant.server import RequestHandler, DEFAULT_CONFIG
from radiant.fake import *

from functools import wraps
import json
import os
from datetime import datetime
import socket


class AutoHTTPServer(ThreadingHTTPServer):

    def __init__(self, server_address, handler_cls):
        ip, port = server_address

        # Decide IPv4 vs IPv6
        if ":" in ip:
            self.address_family = socket.AF_INET6
        else:
            self.address_family = socket.AF_INET

        super().__init__(server_address, handler_cls)


class BrythonServer:
    """Minimal threaded HTTP server wrapper with shared configuration."""

    styles = []
    get_routes = {}
    post_routes = {}
    html_routes = {}

    @classmethod
    def log_server_start(cls, ip, port, server):
        ts = datetime.now().isoformat(timespec="seconds")
        pid = os.getpid()

        if ":" in ip:
            ip = f"[{ip}]"

        if ip in ["[::1]", "127.0.0.1"]:
            localhost = f"(http://localhost:{port}/)"
        else:
            localhost = ""

        print("=" * 70)
        print(f"[{ts}] SERVER BOOT")
        print(f" PID        : {pid}")
        print(f" Class      : {cls.__module__}.{cls.__name__}")
        print(f" Address    : http://{ip}:{port} {localhost}")
        print()
        print(" MODE       : DEVELOPMENT / TEST SERVER")
        print(" WARNING    : NOT FOR PRODUCTION USE")
        print(" PURPOSE    : testing, prototyping, internal experiments only")
        print(" SECURITY   : no hardening, no auth guarantees")
        print()
        print(" Repository : https://github.com/dunderlab/radiant-runtime-bridge")
        print()

        def dump(title, attr):
            routes = getattr(server, attr, {})
            print(f" {title} ({len(routes)})")

            for path, target in routes.items():
                if callable(target):
                    ref = f"{target.__module__}.{target.__qualname__}"
                else:
                    ref = repr(target)

                print(f"   {path:<25} -> {ref}")

            if not routes:
                print("   <none>")
            print()

        def dump_config(config):
            print(" Config     :")
            if not config:
                print("   <empty>")
                return

            excluded_keys = {"class_name"}

            for key in sorted(config):
                if key in excluded_keys:
                    continue
                value = config[key]
                print(f"   {key:<15} = {value!r}")

        dump_config({**DEFAULT_CONFIG, **server.config})
        print()

        dump("GET routes", "get_routes")
        dump("POST routes", "post_routes")
        dump("HTML routes", "html_routes")

        print("=" * 70)

    @classmethod
    def serve(
        cls: Type["BrythonServer"],
        config: Any = {},
        *,
        ip: str = "::1",
        port: int = 5050,
        dist: Optional[str] = None,
    ) -> None:
        """
        Start a threaded HTTP server instance.

        The server attaches a configuration dictionary containing the
        calling class name and any extra keyword arguments. This allows
        the request handler to access runtime metadata through
        ``server.config``.

        Parameters
        ----------
        ip : str, optional
            Hostname or IP address to bind, by default "localhost".
        port : int, optional
            Listening TCP port, by default 8000.
        **kwargs : Any
            Additional configuration values stored in ``server.config``.

        Raises
        ------
        ValueError
            If the port is not a positive integer.
        """

        if not isinstance(port, int) or port <= 0:
            raise ValueError("port must be a positive integer")

        server = AutoHTTPServer((ip, port), RequestHandler)

        server.config: Dict[str, Any] = {
            "class_name": cls.__name__,
            **config,
        }

        server.generate_dist = dist
        server.get_routes = cls.get_routes
        server.post_routes = cls.post_routes
        server.html_routes = cls.html_routes

        # print(f"Server running on http://{ip}:{port}")
        cls.log_server_start(
            ip=ip,
            port=port,
            server=server,
        )

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            # Shutdown to prevent hanging sockets
            server.shutdown()
            server.server_close()

    @classmethod
    def get(cls, route) -> Callable:
        """"""

        def decorator(fn):
            cls.get_routes[route] = fn

            @wraps(fn)
            def wrapper(*args, **kwargs):
                return fn(cls, *args, **kwargs)

            return wrapper

        return decorator

    @classmethod
    def post(cls, route) -> Callable:
        def decorator(fn):
            cls.post_routes[route] = fn

            @wraps(fn)
            def wrapper(*args, **kwargs):
                return fn(*args, **kwargs)

            return wrapper

        return decorator

    @classmethod
    def view(cls, route) -> Callable:
        def decorator(fn):
            cls.html_routes[route] = fn

            @wraps(fn)
            def wrapper(*args, **kwargs):
                return fn(*args, **kwargs)

            return wrapper

        return decorator


def json_response(data: Any, status=200) -> dict:
    return {
        "status": status,
        "body": json.dumps(data).encode("utf-8"),
        "content_type": "application/json",
    }


#
# def html_response(body: str, status=200) -> dict:
#     return {
#         "status": status,
#         "body": body.encode("utf-8"),
#         "content_type": "text/html",
#     }
