# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from bijux_rag.domain.logging import LogEntry, LogMonoid, trace_stage, trace_value
from bijux_rag.fp.effects.writer import run_writer


def test_log_monoid_identity_and_append_order() -> None:
    e1 = LogEntry(level="INFO", msg="a")
    e2 = LogEntry(level="DEBUG", msg="b")
    empty = LogMonoid.empty()

    assert LogMonoid.append(empty, (e1,)) == (e1,)
    assert LogMonoid.append((e1,), empty) == (e1,)
    assert LogMonoid.append((e1,), (e2,)) == (e1, e2)


def test_trace_helpers_produce_structured_entries() -> None:
    _, log1 = run_writer(trace_stage("stage-1"))
    _, log2 = run_writer(trace_value("x", 123))

    assert log1 == (LogEntry(level="INFO", msg="stage-1"),)
    assert log2 == (LogEntry(level="DEBUG", msg="x=123"),)
