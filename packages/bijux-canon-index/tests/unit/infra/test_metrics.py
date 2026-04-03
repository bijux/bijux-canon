# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass, field

from bijux_canon_index.infra.metrics import InMemoryMetrics, timed


@dataclass
class RecordingMetrics:
    counters: dict[str, int] = field(default_factory=dict)
    timers_ms: dict[str, list[float]] = field(default_factory=dict)

    def increment(self, name: str, value: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + value

    def observe_ms(self, name: str, value_ms: float) -> None:
        self.timers_ms.setdefault(name, []).append(value_ms)

    def snapshot(self) -> object:
        return {"counters": self.counters, "timers_ms": self.timers_ms}


def test_in_memory_metrics_snapshot_is_defensive() -> None:
    sink = InMemoryMetrics()

    sink.increment("indexed_total", 2)
    sink.observe_ms("query_latency_ms", 1.5)

    snapshot = sink.snapshot()
    snapshot.counters["indexed_total"] = 99
    snapshot.timers_ms["query_latency_ms"].append(9.9)

    refreshed = sink.snapshot()
    assert refreshed.counters["indexed_total"] == 2
    assert refreshed.timers_ms["query_latency_ms"] == [1.5]


def test_timed_accepts_structural_metrics_sink() -> None:
    sink = RecordingMetrics()

    with timed("query_latency_ms", sink=sink) as elapsed:
        assert elapsed() >= 0.0
        sink.increment("queries_total")

    assert sink.counters["queries_total"] == 1
    assert len(sink.timers_ms["query_latency_ms"]) == 1
    assert sink.timers_ms["query_latency_ms"][0] >= 0.0
