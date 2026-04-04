# INTERNAL — NOT A PUBLIC EXTENSION POINT
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Application-layer orchestration exports for bijux-canon-runtime."""

from __future__ import annotations

from typing import Any

from bijux_canon_runtime.application.flow_boundary import enforce_flow_boundary
from bijux_canon_runtime.application.planner import ExecutionPlanner

__all__ = [
    "ExecutionPlanner",
    "FlowRunResult",
    "RunMode",
    "enforce_flow_boundary",
    "execute_flow",
]


def __getattr__(name: str) -> Any:
    if name == "ExecutionPlanner":
        return ExecutionPlanner
    if name == "enforce_flow_boundary":
        return enforce_flow_boundary
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
