"""Interrupt monitoring that preserves partial state when a run is canceled."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
import signal
from typing import Any

from bijux_agent.pipeline.control.stop_conditions import StopReason


@dataclass
class InterruptMonitor:
    """Tracks POSIX-style interrupts and exposes clean shutdown hooks."""

    _interrupted: bool = field(default=False, init=False)
    _original_handler: Any | None = field(default=None, init=False)

    def activate(self) -> None:
        self._original_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._handle)

    def deactivate(self) -> None:
        if self._original_handler:
            signal.signal(signal.SIGINT, self._original_handler)
            self._original_handler = None

    def trigger(self) -> None:
        self._interrupted = True

    def is_interrupted(self) -> bool:
        return self._interrupted

    def require_stop_reason(self) -> StopReason:
        return StopReason.USER_INTERRUPTION

    def _handle(self, signum: int, frame: object | None) -> None:
        del frame  # Unused
        self._interrupted = True

    @contextmanager
    def watch(self) -> Iterator[InterruptMonitor]:
        try:
            self.activate()
            yield self
        finally:
            self.deactivate()
