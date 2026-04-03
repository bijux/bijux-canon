# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
import time


@dataclass
class MetricsSnapshot:
    counters: dict[str, int]
    timers_ms: dict[str, list[float]]


class MetricsSink:
    def increment(self, name: str, value: int = 1) -> None:
        raise NotImplementedError

    def observe_ms(self, name: str, value_ms: float) -> None:
        raise NotImplementedError

    def snapshot(self) -> MetricsSnapshot:
        raise NotImplementedError


@dataclass
class InMemoryMetrics(MetricsSink):
    counters: dict[str, int] = field(default_factory=dict)
    timers_ms: dict[str, list[float]] = field(default_factory=dict)

    def increment(self, name: str, value: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + int(value)

    def observe_ms(self, name: str, value_ms: float) -> None:
        self.timers_ms.setdefault(name, []).append(float(value_ms))

    def snapshot(self) -> MetricsSnapshot:
        return MetricsSnapshot(
            counters=dict(self.counters),
            timers_ms={k: list(v) for k, v in self.timers_ms.items()},
        )


METRICS: MetricsSink = InMemoryMetrics()


@contextmanager
def timed(
    metric_name: str, sink: MetricsSink | None = None
) -> Iterator[Callable[[], float]]:
    start = time.perf_counter()
    yield lambda: (time.perf_counter() - start) * 1000.0
    duration = (time.perf_counter() - start) * 1000.0
    (sink or METRICS).observe_ms(metric_name, duration)


__all__ = ["METRICS", "MetricsSink", "InMemoryMetrics", "MetricsSnapshot", "timed"]
