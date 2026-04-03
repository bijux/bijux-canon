# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_rar.core.rar_types import (
    Claim,
    ClaimEmittedEvent,
    ClaimStatus,
    ClaimType,
    DeriveOutput,
    Plan,
    PlanNode,
    ProblemSpec,
    StepFinishedEvent,
    StepSpec,
    StepStartedEvent,
    Trace,
    TraceEventKind,
)
from bijux_rar.rar.traces.replay import diff_traces


def test_diff_traces_detects_first_mismatch() -> None:
    spec = ProblemSpec(description="diff test")
    assert spec.id is not None
    step = PlanNode(
        kind="understand", dependencies=[], step=StepSpec(kind="understand")
    )
    assert step.id is not None
    plan = Plan(spec_id=spec.id, nodes=[step])
    assert plan.id is not None

    claim = Claim(
        claim_type=ClaimType.derived,
        statement="ok true",
        structured={"ok": True},
        status=ClaimStatus.proposed,
        confidence=1.0,
        support_refs=[],
    )
    assert claim.id is not None
    base_cid = claim.id

    base_events = [
        StepStartedEvent(idx=0, kind=TraceEventKind.step_started, step_id=step.id),
        ClaimEmittedEvent(idx=1, kind=TraceEventKind.claim_emitted, claim=claim),
        StepFinishedEvent(
            idx=2,
            kind=TraceEventKind.step_finished,
            step_id=step.id,
            output=DeriveOutput(kind="derive", emitted_claim_ids=[base_cid]),
        ),
    ]

    t1 = Trace(
        spec_id=spec.id, plan_id=plan.id, events=base_events, metadata={"seed": 1}
    )

    mutated_events = list(base_events)
    mutated_events[1] = ClaimEmittedEvent(
        idx=1,
        kind=TraceEventKind.claim_emitted,
        claim=Claim(
            claim_type=ClaimType.derived,
            statement="ok false",
            structured={"ok": False},
            status=ClaimStatus.proposed,
            confidence=1.0,
            support_refs=[],
        ),
    )
    t2 = Trace(
        spec_id=spec.id, plan_id=plan.id, events=mutated_events, metadata={"seed": 1}
    )

    diff = diff_traces(t1, t2)
    assert diff["identical"] is False
    assert diff["first_mismatch_idx"] == 1
    assert "original_event" in diff
    assert "replayed_event" in diff
