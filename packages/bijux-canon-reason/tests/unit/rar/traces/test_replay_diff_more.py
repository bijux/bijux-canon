# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_rar.core.rar_types import Trace
from bijux_rar.rar.traces.replay import diff_traces


def test_diff_traces_identical_short_circuit() -> None:
    t = Trace(spec_id="s", plan_id="p", events=[], metadata={})
    diff = diff_traces(t, t)
    assert diff["identical"] is True
    assert diff["first_mismatch_idx"] is None
    assert diff["changed_event_kinds"] == {}


def test_diff_traces_reports_length_mismatch() -> None:
    from bijux_rar.core.rar_types import StepStartedEvent, TraceEventKind

    ev_a = StepStartedEvent(
        idx=0, kind=TraceEventKind.step_started, step_id="step-A"
    )
    ev_b = StepStartedEvent(
        idx=0, kind=TraceEventKind.step_started, step_id="step-B"
    )
    t1 = Trace(spec_id="s", plan_id="p", events=[ev_a], metadata={})
    t2 = Trace(spec_id="s", plan_id="p", events=[ev_b], metadata={})
    diff = diff_traces(t1, t2)
    assert diff["identical"] is False
    assert diff["first_mismatch_idx"] == 0
