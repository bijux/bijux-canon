"""Minimal ASGI entrypoint for the v1 HTTP surface."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from .asgi_support import (
    ASGIReceive,
    ASGISend,
    handle_health,
    handle_run,
    normalize_path,
    send_json,
)

ASGIApp = Callable[
    [
        dict[str, Any],
        ASGIReceive,
        ASGISend,
    ],
    Awaitable[None],
]


def create_app() -> ASGIApp:
    """Create the v1 ASGI application."""

    async def app(
        scope: dict[str, Any],
        receive: ASGIReceive,
        send: ASGISend,
    ) -> None:
        if scope.get("type") != "http":
            return

        method = str(scope.get("method", "GET")).upper()
        path = normalize_path(str(scope.get("path", "/")))

        if path == "/health":
            await handle_health(method=method, send=send)
            return

        if path == "/run":
            await handle_run(method=method, receive=receive, send=send)
            return

        await send_json(send, status=404, payload={"error": "not found"})

    return app


__all__ = ["create_app"]
