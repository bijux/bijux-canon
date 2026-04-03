# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Public package exports for bijux-canon-runtime."""

from __future__ import annotations

from bijux_canon_runtime.model.flows.manifest import FlowManifest
from typing import Any

__all__ = [
    "FlowManifest",
    "RunMode",
    "execute_flow",
]


def __getattr__(name: str) -> Any:
    if name == "FlowManifest":
        return FlowManifest
    if name in {"RunMode", "execute_flow"}:
        from bijux_canon_runtime.application.execute_flow import RunMode, execute_flow

        exports = {
            "RunMode": RunMode,
            "execute_flow": execute_flow,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
