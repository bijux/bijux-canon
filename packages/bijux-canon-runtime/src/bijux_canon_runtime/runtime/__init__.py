# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Runtime support exports for bijux-canon-runtime."""

from __future__ import annotations

from typing import Any

__all__ = ["FlowRunResult", "RunMode", "execute_flow"]


def __getattr__(name: str) -> Any:
    """Lazily resolve exported attributes."""
    if name in {"FlowRunResult", "RunMode", "execute_flow"}:
        from bijux_canon_runtime.application.execute_flow import (
            FlowRunResult,
            RunMode,
            execute_flow,
        )

        exports = {
            "FlowRunResult": FlowRunResult,
            "RunMode": RunMode,
            "execute_flow": execute_flow,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
