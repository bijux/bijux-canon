# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""HTTP guards helpers for API support."""

from __future__ import annotations

import json
import time

from fastapi import HTTPException, Request

from bijux_canon_reason.interfaces.access_guards import rate_limit_per_key

MAX_REQUEST_BYTES = 8192
MAX_RESPONSE_ITEMS = 100
MAX_OFFSET = 1_000_000
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
DENY_CONTENT_TYPES = {"application/xml", "text/xml"}


def initialize_rate_limit_state(limit: int) -> dict[str, object]:
    """Initialize rate limit state."""
    return {
        "limit": limit,
        "window_start": time.time(),
        "count": 0,
        "buckets": {},
    }


def guard_request(
    request: Request,
    *,
    api_token: str | None,
    rate_limit: int,
    rate_limit_state: dict[str, object],
) -> None:
    """Handle guard request."""
    _check_size_limit(request)
    supplied = request.headers.get("x-api-token")
    if api_token and supplied != api_token:
        raise HTTPException(status_code=401, detail="unauthorized")
    if request.headers.get("content-type"):
        content_type = request.headers["content-type"].split(";")[0].strip().lower()
        if content_type in DENY_CONTENT_TYPES:
            raise HTTPException(status_code=415, detail="unsupported media type")
    if rate_limit > 0:
        try:
            rate_limit_per_key(rate_limit_state, supplied or "anon")
        except PermissionError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc


def enforce_response_size(payload: dict[str, object]) -> dict[str, object]:
    """Enforce response size."""
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_RESPONSE_BYTES:
        raise HTTPException(status_code=413, detail="response too large")
    return payload


def _check_size_limit(request: Request) -> None:
    """Handle check size limit."""
    content_length = request.headers.get("content-length")
    if content_length is None:
        return
    try:
        if int(content_length) > MAX_REQUEST_BYTES:
            raise HTTPException(status_code=413, detail="request too large")
    except ValueError:
        return


__all__ = [
    "DENY_CONTENT_TYPES",
    "MAX_OFFSET",
    "MAX_REQUEST_BYTES",
    "MAX_RESPONSE_BYTES",
    "MAX_RESPONSE_ITEMS",
    "enforce_response_size",
    "guard_request",
    "initialize_rate_limit_state",
]
