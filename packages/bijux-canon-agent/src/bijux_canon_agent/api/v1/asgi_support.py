"""Shared ASGI helpers for the v1 HTTP application."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable
import json
from typing import Any

from pydantic import ValidationError

from bijux_canon_agent.api.v1.errors import APIErrorCode, HTTP_STATUS_BY_CODE
from bijux_canon_agent.api.v1.handlers import run_pipeline_v1
from bijux_canon_agent.api.v1.schemas import ErrorResponseV1, RunRequestV1
from bijux_canon_agent.core.version import get_runtime_version

ASGIReceive = Callable[[], Awaitable[dict[str, Any]]]
ASGISend = Callable[[dict[str, Any]], Awaitable[None]]
Headers = list[tuple[bytes, bytes]]


def normalize_path(path: str) -> str:
    """Normalize an incoming HTTP path for v1 routing."""
    if not path:
        return "/"
    while path.startswith("/v1/"):
        path = path[len("/v1") :]
    if path == "/v1":
        return "/"
    return path if path.startswith("/") else f"/{path}"


def _json_dumps(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _response_messages(
    status: int, payload: dict[str, Any], headers: Headers | None = None
) -> Iterable[dict[str, Any]]:
    body = _json_dumps(payload)
    response_headers: Headers = [(b"content-type", b"application/json")]
    if headers:
        response_headers.extend(headers)
    yield {"type": "http.response.start", "status": status, "headers": response_headers}
    yield {"type": "http.response.body", "body": body}


async def send_json(
    send: ASGISend,
    status: int,
    payload: dict[str, Any],
    headers: Headers | None = None,
) -> None:
    """Send a JSON response through the ASGI channel."""
    for message in _response_messages(status=status, payload=payload, headers=headers):
        await send(message)


async def _read_body(receive: ASGIReceive) -> bytes:
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
    http_status = HTTP_STATUS_BY_CODE[code]
    return ErrorResponseV1(
        code=code.value,
        message=message,
        http_status=http_status,
    ).model_dump()


async def handle_health(method: str, send: ASGISend) -> None:
    """Serve the health route with GET-only semantics."""
    if method != "GET":
        await send_json(
            send,
            status=405,
            payload={"error": "method not allowed"},
            headers=[(b"allow", b"GET")],
        )
        return
    await send_json(
        send,
        status=200,
        payload={"status": "ok", "version": get_runtime_version()},
    )


async def handle_run(method: str, receive: ASGIReceive, send: ASGISend) -> None:
    """Serve the run route with schema validation and error mapping."""
    if method != "POST":
        await send_json(
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
        await send_json(send, status=payload["http_status"], payload=payload)
        return

    try:
        response = await asyncio.to_thread(run_pipeline_v1, request)
    except Exception as exc:  # pragma: no cover
        payload = _error_payload(APIErrorCode.INTERNAL_ERROR, str(exc))
        await send_json(send, status=payload["http_status"], payload=payload)
        return

    if response.error is not None:
        err = response.error.model_dump()
        await send_json(send, status=response.error.http_status, payload=err)
        return

    await send_json(send, status=200, payload=response.model_dump())
