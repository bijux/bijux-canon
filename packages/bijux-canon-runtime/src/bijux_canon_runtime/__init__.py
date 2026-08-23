# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Public package exports for bijux-canon-runtime."""

from __future__ import annotations

from typing import Any

from bijux_canon_runtime.model.flows.manifest import FlowManifest

__all__ = [
    "FlowManifest",
    "RuntimeCapabilityDiscovery",
    "RunMode",
    "discover_runtime_capabilities",
    "execute_flow",
]


def __getattr__(name: str) -> Any:
    """Lazily resolve exported attributes."""
    if name == "FlowManifest":
        return FlowManifest
    if name in {"RunMode", "execute_flow"}:
        from bijux_canon_runtime.application.execute_flow import RunMode, execute_flow

        exports = {
            "RunMode": RunMode,
            "execute_flow": execute_flow,
        }
        return exports[name]
    if name in {"RuntimeCapabilityDiscovery", "discover_runtime_capabilities"}:
        from bijux_canon_runtime.application.capability_discovery import (
            RuntimeCapabilityDiscovery,
            discover_runtime_capabilities,
        )

        exports = {
            "RuntimeCapabilityDiscovery": RuntimeCapabilityDiscovery,
            "discover_runtime_capabilities": discover_runtime_capabilities,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
