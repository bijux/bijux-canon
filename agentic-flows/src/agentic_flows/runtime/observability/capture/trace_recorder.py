# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/observability/capture/trace_recorder.py."""

from __future__ import annotations

from collections.abc import Iterable

from agentic_flows.core.authority import AuthorityToken
from agentic_flows.spec.model.identifiers.execution_event import ExecutionEvent


class AppendOnlyList(list[ExecutionEvent]):
    """Behavioral contract for AppendOnlyList."""

    def __setitem__(self, *_args, **_kwargs) -> None:
        """Internal helper; not part of the public API."""
        raise TypeError("execution events are append-only")

    def __delitem__(self, *_args, **_kwargs) -> None:
        """Internal helper; not part of the public API."""
        raise TypeError("execution events are append-only")

    def clear(self) -> None:
        """Execute clear and enforce its contract."""
        raise TypeError("execution events are append-only")

    def extend(self, _iterable: Iterable[ExecutionEvent]) -> None:
        """Execute extend and enforce its contract."""
        raise TypeError("execution events are append-only")

    def insert(self, _index: int, _value: ExecutionEvent) -> None:
        """Execute insert and enforce its contract."""
        raise TypeError("execution events are append-only")

    def pop(self, _index: int = -1) -> ExecutionEvent:
        """Execute pop and enforce its contract."""
        raise TypeError("execution events are append-only")

    def remove(self, _value: ExecutionEvent) -> None:
        """Execute remove and enforce its contract."""
        raise TypeError("execution events are append-only")

    def reverse(self) -> None:
        """Execute reverse and enforce its contract."""
        raise TypeError("execution events are append-only")

    def sort(self, *_args, **_kwargs) -> None:
        """Execute sort and enforce its contract."""
        raise TypeError("execution events are append-only")


class TraceRecorder:
    """Behavioral contract for TraceRecorder."""

    def __init__(self, events: Iterable[ExecutionEvent] | None = None) -> None:
        """Internal helper; not part of the public API."""
        self._events: AppendOnlyList = AppendOnlyList(list(events or ()))

    def record(self, event: ExecutionEvent, authority: AuthorityToken) -> None:
        """Execute record and enforce its contract."""
        if not isinstance(authority, AuthorityToken):
            raise TypeError("authority token required to record execution events")
        self._events.append(event)

    def events(self) -> tuple[ExecutionEvent, ...]:
        """Execute events and enforce its contract."""
        return tuple(self._events)
