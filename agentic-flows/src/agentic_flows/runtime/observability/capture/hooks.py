# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/observability/capture/hooks.py."""

from __future__ import annotations

from typing import Protocol

from agentic_flows.spec.model.identifiers.execution_event import ExecutionEvent


class RuntimeObserver(Protocol):
    """Runtime observer contract; misuse breaks observation guarantees."""

    def on_event(self, event: ExecutionEvent) -> None:
        """Execute on_event and enforce its contract."""
        ...


__all__ = ["RuntimeObserver"]
