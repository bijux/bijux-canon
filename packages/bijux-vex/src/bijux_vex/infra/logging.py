# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import json
import logging
import os
from typing import Any

_LOGGER = logging.getLogger("bijux_vex")
_TRACE_ENABLED = False
_TRACE_EVENTS: list[dict[str, Any]] = []


def log_event(name: str, **fields: Any) -> None:
    if not _LOGGER.handlers:
        logging.basicConfig(level=logging.INFO)
    payload = {"event": name, **fields}
    fmt = (os.getenv("BIJUX_VEX_LOG_FORMAT") or "").lower()
    if fmt == "json":
        _LOGGER.info(json.dumps(payload, sort_keys=True))
    else:
        rendered = " ".join(f"{k}={v}" for k, v in payload.items())
        _LOGGER.info(rendered)
    if _TRACE_ENABLED:
        _TRACE_EVENTS.append(payload)


def enable_trace() -> None:
    global _TRACE_ENABLED
    _TRACE_ENABLED = True


def trace_events() -> list[dict[str, Any]]:
    return list(_TRACE_EVENTS)


__all__ = ["log_event", "enable_trace", "trace_events"]
