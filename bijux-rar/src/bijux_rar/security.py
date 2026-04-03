# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""
Security utilities for boundary layers.

SPDX-FileCopyrightText: © 2025 Bijan Mousavi
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import re
import time
from typing import Any

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def sanitize_run_id(run_id: str) -> str:
    """Validate and normalize run identifiers used in HTTP paths."""
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("invalid run_id")
    return run_id


def require_api_key(headers: Any, *, expected: str | None) -> None:
    """Enforce API key header if an expected key is configured."""
    if not expected:
        return
    provided = headers.get("x-api-key")
    if provided != expected:
        raise PermissionError("unauthorized")


def rate_limit_stateful(state: dict[str, Any]) -> None:
    """Simple in-memory rate limiter (best effort, process local).

    state keys:
      limit: int (0 = disabled)
      window_start: float (epoch seconds)
      count: int
    """
    limit = int(state.get("limit", 0))
    if limit <= 0:
        return
    window_start = float(state.get("window_start", time.time()))
    now = time.time()
    if now - window_start > 60.0:
        state["window_start"] = now
        state["count"] = 0
    count = int(state.get("count", 0))
    if count >= limit:
        raise PermissionError("rate limit exceeded")
    state["count"] = count + 1


def rate_limit_per_key(state: dict[str, Any], key: str) -> None:
    """Per-key best-effort limiter: state maps key -> bucket."""
    limit = int(state.get("limit", 0))
    if limit <= 0:
        return
    buckets = state.setdefault("buckets", {})
    bucket = buckets.get(key) or {"window_start": time.time(), "count": 0}
    now = time.time()
    if now - bucket["window_start"] > 60.0:
        bucket = {"window_start": now, "count": 0}
    bucket["count"] += 1
    if bucket["count"] > limit:
        buckets[key] = bucket
        raise PermissionError("rate limit exceeded")
    buckets[key] = bucket
