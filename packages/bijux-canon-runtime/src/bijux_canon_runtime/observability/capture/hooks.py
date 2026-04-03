# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for observability/capture/hooks.py."""

from __future__ import annotations

from typing import Protocol

from bijux_canon_runtime.model.identifiers.execution_event import ExecutionEvent


class RuntimeObserver(Protocol):
    """Runtime observer contract; misuse breaks observation guarantees."""

    def on_event(self, event: ExecutionEvent) -> None:
        """Execute on_event and enforce its contract."""
        ...


__all__ = ["RuntimeObserver"]
