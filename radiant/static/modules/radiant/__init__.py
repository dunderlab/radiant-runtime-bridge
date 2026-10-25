from typing import Any, Callable

from radiant.core import Element, html, select
from fake import Fake

from browser import ajax
from urllib.parse import urlencode
from browser import window, document
import json
import os

from functools import wraps


class BrythonServer:
    """
    Integration helper exposing Radiant core primitives.

    This class provides convenient access to HTML generation, element
    selection, and element enhancement utilities.
    """

    # Exposed core utilities as class attributes for easy access
    select = select
    html = html
    document = document
    window = window

    def enhance(self, element: Any) -> Element:
        """
        Enhance an existing element with Radiant helpers.

        Parameters
        ----------
        element : Any
            An HTML-like element to wrap.

        Returns
        -------
        Element
            An enhanced Element wrapper.
        """
        return Element(element)

    @classmethod
    def get(cls, route: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator for defining HTTP GET-based client handlers.

        Parameters
        ----------
        route : str
            Base route for the GET request.

        Returns
        -------
        Callable
            A decorator that wraps a function with GET-fetch behavior.
        """

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            # @wraps(fn)
            # def wrapper(cls, **kwargs: Any) -> Any:
            #     if kwargs:
            #         query = urlencode(kwargs, doseq=True)
            #         url = f"{route}?{query}"
            #     else:
            #         url = route
            #     return (
            #         window.fetch(url)
            #         .then(lambda r: r.text())
            #         .then(lambda text: json.loads(text))
            #     )
            #
            # return wrapper

            class wrapper:

                def call(self, **kwargs: Any) -> Any:
                    """"""
                    if kwargs:
                        query = urlencode(kwargs, doseq=True)
                        url = f"{route}?{query}"
                    else:
                        url = route
                    return (
                        window.fetch(url)
                        .then(lambda r: r.text())
                        .then(lambda text: json.loads(text))
                    )

            return wrapper()

        return decorator

    @classmethod
    def post(cls, route: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator for defining HTTP POST-based client handlers.

        Parameters
        ----------
        route : str
            Target route for the POST request.

        Returns
        -------
        Callable
            A decorator that wraps a function with POST-fetch behavior.
        """

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            # @wraps(fn)
            # def wrapper(**kwargs: Any) -> Any:
            #     body = json.dumps(kwargs)
            #
            #     return (
            #         window.fetch(
            #             route,
            #             {
            #                 "method": "POST",
            #                 "headers": {"Content-Type": "application/json"},
            #                 "body": body,
            #             },
            #         )
            #         .then(lambda r: r.text())
            #         .then(lambda text: json.loads(text))
            #     )
            #
            # return wrapper

            class wrapper:

                def call(self, **kwargs: Any) -> Any:
                    """"""
                    body = json.dumps(kwargs)

                    return (
                        window.fetch(
                            route,
                            {
                                "method": "POST",
                                "headers": {"Content-Type": "application/json"},
                                "body": body,
                            },
                        )
                        .then(lambda r: r.text())
                        .then(lambda text: json.loads(text))
                    )

            return wrapper()

        return decorator

    @classmethod
    def view(cls, route: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator for registering a view handler.

        This decorator currently acts as a pass-through and exists
        for semantic consistency with other route decorators.

        Parameters
        ----------
        route : str
            Route associated with the view.

        Returns
        -------
        Callable
            A decorator that returns the original function unchanged.
        """

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(fn)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                return fn(*args, **kwargs)

            return wrapper

        return decorator

    def add_css_file(self, file):
        """
        Adds a CSS file to the document's head element.

        This method appends a CSS link element to the <head> section of the document,
        allowing the specific CSS file to be applied to the webpage. The CSS file path
        should be relative to the specified root directory defined in the `href`.

        Parameters
        ----------
        file : str
            The relative path to the CSS file to be added. This path will be combined
            with the root directory to correctly locate the file.
        """
        document.select("head")[0] <= html.LINK(
            href=file, type="text/css", rel="stylesheet"
        )
        document.select("head")[0] <= html.LINK(
            href=f"static/{file}", type="text/css", rel="stylesheet"
        )


json_response = Fake()
