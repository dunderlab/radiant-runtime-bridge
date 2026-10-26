# Base class that binds the Python server with the Brython frontend
from radiant import BrythonServer


class App(BrythonServer):
    # Minimal application demonstrating static assets and CSS injection

    def __init__(self):
        # Register an external CSS file to be injected into the HTML head
        self.add_css_file("styles.css")

        self.document <= self.html.H1("Radiant · Python Runtime Bridge")
        self.document <= self.html.P(
            "This application connects a Python backend with a Brython-powered frontend "
            "through a unified runtime."
        )


if __name__ == "__main__":
    # Start the server and expose static directories
    # The 'static' key maps URL paths to filesystem folders
    App.serve(
        {
            "static": ["static"],
        }
    )
