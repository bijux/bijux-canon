"""
Minimal ASGI HTTP adapter.

This module exposes a tiny, framework-free ASGI application for the bijux-agent
API. It is intentionally small and deterministic to support:

- local dev runs (`make api`)
- contract testing (Schemathesis/OpenAPI validation)
- execution of the canonical pipeline behind a stable HTTP surface

Routes (mounted at `/v1` by the runner):
- GET  /health   -> {"status": "ok", "version": "..."}
- POST /run      -> Run the canonical pipeline

Error semantics:
- Request parse/validation errors -> structured `ErrorResponseV1` with the
  corresponding HTTP status from `HTTP_STATUS_BY_CODE`.
- Unexpected internal failures -> structured `ErrorResponseV1`.

Design notes:
- No framework dependency: implements ASGI directly.
- Reads full request body into memory (acceptable for test/dev use).
- Offloads pipeline execution to a worker thread to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable
import json
from typing import Any

from pydantic import ValidationError

from bijux_agent.api.v1.errors import HTTP_STATUS_BY_CODE, APIErrorCode
from bijux_agent.api.v1.handlers import run_pipeline_v1
from bijux_agent.api.v1.schemas import ErrorResponseV1, RunRequestV1
from bijux_agent.utilities.version import get_runtime_version

ASGIApp = Callable[
    [
        dict[str, Any],
        Callable[[], Awaitable[dict[str, Any]]],
        Callable[[dict[str, Any]], Awaitable[None]],
    ],
    Awaitable[None],
]
Headers = list[tuple[bytes, bytes]]


def _normalize_path(path: str) -> str:
    """
    Normalize a request path for v1 routing.

    The API test runner typically mounts the app at `/v1`. This function accepts
    either of these inputs:

    - `/v1/run` or `/run` -> `/run`
    - `/v1/health` or `/health` -> `/health`

    It also tolerates an odd `/v1` path and normalizes it to `/`.
    """
    if not path:
        return "/"

    # Strip any number of leading "/v1" prefixes (defensive).
    while path.startswith("/v1/"):
        path = path[len("/v1") :]

    if path == "/v1":
        return "/"

    # Ensure leading slash.
    return path if path.startswith("/") else f"/{path}"


def _json_dumps(payload: dict[str, Any]) -> bytes:
    """
    Serialize a JSON payload to UTF-8 bytes.

    Using explicit UTF-8 encoding keeps this adapter deterministic and avoids
    implicit encoding behaviors.
    """
    return json.dumps(payload).encode("utf-8")


def _response_messages(
    status: int,
    payload: dict[str, Any],
    headers: Headers | None = None,
) -> Iterable[dict[str, Any]]:
    """
    Build ASGI response messages for a JSON response.

    Returns an iterator of two ASGI messages:
    - http.response.start
    - http.response.body
    """
    body = _json_dumps(payload)
    response_headers: Headers = [(b"content-type", b"application/json")]
    if headers:
        response_headers.extend(headers)

    yield {"type": "http.response.start", "status": status, "headers": response_headers}
    yield {"type": "http.response.body", "body": body}


async def _send_json(
    send: Callable[[dict[str, Any]], Awaitable[None]],
    status: int,
    payload: dict[str, Any],
    headers: Headers | None = None,
) -> None:
    """Send a JSON response via ASGI `send`."""
    for message in _response_messages(status=status, payload=payload, headers=headers):
        await send(message)


async def _read_body(receive: Callable[[], Awaitable[dict[str, Any]]]) -> bytes:
    """
    Read the full HTTP request body from ASGI `receive`.

    This adapter reads the entire body into memory. That is acceptable for
    tests/dev, and keeps the implementation simple and deterministic.
    """
    chunks: list[bytes] = []
    while True:
        message = await receive()
        if message.get("type") != "http.request":
            continue
        chunks.append(message.get("body", b""))
        if not message.get("more_body", False):
            break
    return b"".join(chunks)


def _error_payload(code: APIErrorCode, message: str) -> dict[str, Any]:
    """
    Build a structured error payload as documented by the API schema.
    """
    http_status = HTTP_STATUS_BY_CODE[code]
    return ErrorResponseV1(
        code=code.value,
        message=message,
        http_status=http_status,
    ).model_dump()


async def _handle_health(
    method: str, send: Callable[[dict[str, Any]], Awaitable[None]]
) -> None:
    """
    Handle the health endpoint.

    - GET -> 200
    - otherwise -> 405 with Allow header
    """
    if method != "GET":
        await _send_json(
            send,
            status=405,
            payload={"error": "method not allowed"},
            headers=[(b"allow", b"GET")],
        )
        return

    await _send_json(
        send,
        status=200,
        payload={"status": "ok", "version": get_runtime_version()},
    )


async def _handle_run(
    method: str,
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    """
    Handle the pipeline run endpoint.

    - POST with JSON body -> runs pipeline and returns `RunResponseV1` as JSON
    - Non-POST -> 405 with Allow header
    - Bad JSON / schema validation -> structured validation error
    - Execution failures -> structured error response from handler
    """
    if method != "POST":
        await _send_json(
            send,
            status=405,
            payload={"error": "method not allowed"},
            headers=[(b"allow", b"POST")],
        )
        return

    body = await _read_body(receive)

    try:
        raw = json.loads(body.decode("utf-8") or "{}")
        request = RunRequestV1.model_validate(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        payload = _error_payload(APIErrorCode.VALIDATION_ERROR, str(exc))
        await _send_json(send, status=payload["http_status"], payload=payload)
        return

    try:
        # The pipeline code is synchronous; run it in a worker thread.
        response = await asyncio.to_thread(run_pipeline_v1, request)
    except Exception as exc:  # pragma: no cover (defensive mapping)
        payload = _error_payload(APIErrorCode.INTERNAL_ERROR, str(exc))
        await _send_json(send, status=payload["http_status"], payload=payload)
        return

    # Preserve handler semantics:
    # - if response.error is present, return its status and payload
    # - otherwise 200 with the full response body
    if response.error is not None:
        err = response.error.model_dump()
        await _send_json(send, status=response.error.http_status, payload=err)
        return

    await _send_json(send, status=200, payload=response.model_dump())


def create_app() -> ASGIApp:
    """
    Create the ASGI application.

    The returned callable conforms to the ASGI interface:

        app(scope, receive, send) -> await None

    Only `scope["type"] == "http"` is handled; other scope types are ignored.
    """

    async def app(
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        if scope.get("type") != "http":
            return

        method = str(scope.get("method", "GET")).upper()
        path = _normalize_path(str(scope.get("path", "/")))

        if path == "/health":
            await _handle_health(method=method, send=send)
            return

        if path == "/run":
            await _handle_run(method=method, receive=receive, send=send)
            return

        await _send_json(send, status=404, payload={"error": "not found"})

    return app


__all__ = ["create_app"]
