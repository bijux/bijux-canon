# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_rar.core.rar_types import (
    FinalizeOutput,
    GatherOutput,
    InsufficientEvidenceOutput,
    Plan,
    PlanNode,
    ProblemSpec,
    StepFinishedEvent,
    StepSpec,
    StepStartedEvent,
    Trace,
    TraceEventKind,
    UnderstandOutput,
    VerifyOutput,
)
from bijux_rar.rar.verification.verifier import verify_trace


def test_insufficient_evidence_allowed() -> None:
    spec = ProblemSpec(description="q", constraints={}, expected={})
    n_understand = PlanNode(kind="understand", dependencies=[], parameters={})
    n_gather = PlanNode(kind="gather", dependencies=[n_understand.id], step=StepSpec(kind="gather"))
    n_derive = PlanNode(kind="derive", dependencies=[n_gather.id], step=StepSpec(kind="derive"))
    n_verify = PlanNode(kind="verify", dependencies=[n_derive.id], step=StepSpec(kind="verify"))
    n_finalize = PlanNode(kind="finalize", dependencies=[n_verify.id], step=StepSpec(kind="finalize"))
    plan = Plan(spec_id=spec.id, nodes=[n_understand, n_gather, n_derive, n_verify, n_finalize]).with_content_id()

    events = [
        StepStartedEvent(idx=0, kind=TraceEventKind.step_started, step_id=n_understand.id),
        StepFinishedEvent(
            idx=1,
            kind=TraceEventKind.step_finished,
            step_id=n_understand.id,
            output=UnderstandOutput(normalized_question=spec.description, assumptions=[]),
        ),
        StepStartedEvent(idx=2, kind=TraceEventKind.step_started, step_id=n_gather.id),
        StepFinishedEvent(
            idx=3,
            kind=TraceEventKind.step_finished,
            step_id=n_gather.id,
            output=GatherOutput(evidence_ids=[], retrieval_queries=[spec.description]),
        ),
        StepStartedEvent(idx=4, kind=TraceEventKind.step_started, step_id=n_derive.id),
        StepFinishedEvent(
            idx=5,
            kind=TraceEventKind.step_finished,
            step_id=n_derive.id,
            output=InsufficientEvidenceOutput(retrieved=0, required=2),
        ),
        StepStartedEvent(idx=6, kind=TraceEventKind.step_started, step_id=n_verify.id),
        StepFinishedEvent(
            idx=7,
            kind=TraceEventKind.step_finished,
            step_id=n_verify.id,
            output=VerifyOutput(
                validated_claim_ids=[], rejected_claim_ids=[], missing_support_claim_ids=[]
            ),
        ),
        StepStartedEvent(idx=8, kind=TraceEventKind.step_started, step_id=n_finalize.id),
        StepFinishedEvent(
            idx=9,
            kind=TraceEventKind.step_finished,
            step_id=n_finalize.id,
            output=FinalizeOutput(final_claim_ids=[], final_answer=None, uncertainty="No validated claim"),
        ),
    ]

    trace = Trace(
        id="",
        spec_id=spec.id,
        plan_id=plan.id,
        events=events,
        metadata={"reasoning_policy": {"min_supports_per_claim": 2}},
    ).with_content_id()

    report = verify_trace(trace=trace, plan=plan, artifacts_dir=None)
    assert not report.failures
