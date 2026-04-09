# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Logging helpers."""

from __future__ import annotations

import json
import logging
from typing import Any

from bijux_canon_index.infra.environment import read_env

_LOGGER = logging.getLogger("bijux_canon_index")
_TRACE_ENABLED = False
_TRACE_EVENTS: list[dict[str, Any]] = []


def log_event(name: str, **fields: Any) -> None:
    """Handle log event."""
    if not _LOGGER.handlers:
        logging.basicConfig(level=logging.INFO)
    payload = {"event": name, **fields}
    fmt = (
        read_env(
            "BIJUX_CANON_INDEX_LOG_FORMAT",
            legacy="BIJUX_VEX_LOG_FORMAT",
            default="",
        )
        or ""
    ).lower()
    if fmt == "json":
        _LOGGER.info(json.dumps(payload, sort_keys=True))
    else:
        rendered = " ".join(f"{k}={v}" for k, v in payload.items())
        _LOGGER.info(rendered)
    if _TRACE_ENABLED:
        _TRACE_EVENTS.append(payload)


def enable_trace() -> None:
    """Handle enable trace."""
    global _TRACE_ENABLED
    _TRACE_ENABLED = True


def trace_events() -> list[dict[str, Any]]:
    """Handle trace events."""
    return list(_TRACE_EVENTS)


__all__ = ["log_event", "enable_trace", "trace_events"]
