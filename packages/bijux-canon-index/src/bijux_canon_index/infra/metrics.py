# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Metrics helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
import time
from typing import Protocol


@dataclass
class MetricsSnapshot:
    """Represents metrics snapshot."""
    counters: dict[str, int]
    timers_ms: dict[str, list[float]]


class MetricsSink(Protocol):
    """Represents metrics sink."""
    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter metric."""

        ...

    def observe_ms(self, name: str, value_ms: float) -> None:
        """Record a duration in milliseconds."""

        ...

    def snapshot(self) -> MetricsSnapshot:
        """Return the current metrics snapshot."""

        ...


@dataclass
class InMemoryMetrics:
    """Represents in memory metrics."""
    counters: dict[str, int] = field(default_factory=dict)
    timers_ms: dict[str, list[float]] = field(default_factory=dict)

    def increment(self, name: str, value: int = 1) -> None:
        """Handle increment."""
        self.counters[name] = self.counters.get(name, 0) + int(value)

    def observe_ms(self, name: str, value_ms: float) -> None:
        """Handle observe ms."""
        self.timers_ms.setdefault(name, []).append(float(value_ms))

    def snapshot(self) -> MetricsSnapshot:
        """Handle snapshot."""
        return MetricsSnapshot(
            counters=dict(self.counters),
            timers_ms={k: list(v) for k, v in self.timers_ms.items()},
        )


METRICS: MetricsSink = InMemoryMetrics()


@contextmanager
def timed(
    metric_name: str, sink: MetricsSink | None = None
) -> Iterator[Callable[[], float]]:
    """Handle timed."""
    start = time.perf_counter()
    yield lambda: (time.perf_counter() - start) * 1000.0
    duration = (time.perf_counter() - start) * 1000.0
    (sink or METRICS).observe_ms(metric_name, duration)


__all__ = ["METRICS", "MetricsSink", "InMemoryMetrics", "MetricsSnapshot", "timed"]
