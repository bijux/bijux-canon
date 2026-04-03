# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_rar.core.rar_types import (
    Claim,
    ClaimEmittedEvent,
    ClaimStatus,
    ClaimType,
    DeriveOutput,
    EvidenceRef,
    EvidenceRegisteredEvent,
    FinalizeOutput,
    GatherOutput,
    Plan,
    PlanNode,
    ProblemSpec,
    StepFinishedEvent,
    StepSpec,
    StepStartedEvent,
    SupportKind,
    SupportRef,
    ToolCall,
    ToolCalledEvent,
    ToolResult,
    ToolReturnedEvent,
    Trace,
    TraceEventKind,
    UnderstandOutput,
    VerifyOutput,
)
from bijux_rar.rar.verification.verifier import verify_trace


def test_verifier_passes_on_valid_trace_with_plan() -> None:
    spec = ProblemSpec(description="x", constraints={}, expected={})
    assert spec.id is not None
    spec_id = spec.id
    n_understand = PlanNode(kind="understand", dependencies=[], parameters={})
    assert n_understand.id is not None
    n_gather = PlanNode(
        kind="gather",
        dependencies=[n_understand.id],
        step=StepSpec(kind="gather"),
        parameters={},
    )
    assert n_gather.id is not None
    n_derive = PlanNode(
        kind="derive",
        dependencies=[n_gather.id],
        step=StepSpec(kind="derive"),
        parameters={},
    )
    assert n_derive.id is not None
    n_verify = PlanNode(
        kind="verify",
        dependencies=[n_derive.id],
        step=StepSpec(kind="verify"),
        parameters={},
    )
    assert n_verify.id is not None
    n_finalize = PlanNode(
        kind="finalize",
        dependencies=[n_verify.id],
        step=StepSpec(kind="finalize"),
        parameters={},
    )
    assert n_finalize.id is not None
    nodes = [n_understand, n_gather, n_derive, n_verify, n_finalize]
    plan = Plan(spec_id=spec_id, nodes=nodes)
    assert plan.id is not None
    plan_id = plan.id

    gather_id = n_gather.id
    derive_id = n_derive.id
    verify_id = n_verify.id
    finalize_id = n_finalize.id
    understand_id = n_understand.id
    call = ToolCall(
        step_id=gather_id, call_idx=0, tool_name="retrieve", arguments={"q": "x"}
    )
    assert call.id is not None
    res = ToolResult(call_id=call.id, ok=True, result={"ok": True}, error=None)

    ev_ref = EvidenceRef(
        id="ev1",
        uri="mem://doc",
        sha256="0" * 64,
        span=(0, 1),
        chunk_id="1" * 64,
        content_path="",
    )
    claim = Claim(
        claim_type=ClaimType.derived,
        statement=f"x=1 [evidence:{ev_ref.id}:0-1:{'0' * 64}]",
        structured={"x": 1, "result_sha256": "0" * 64},
        status=ClaimStatus.proposed,
        confidence=1.0,
        supports=[
            SupportRef(
                kind=SupportKind.evidence,
                ref_id=ev_ref.id,
                span=(0, 1),
                snippet_sha256="0" * 64,
            ),
            SupportRef(
                kind=SupportKind.tool_call,
                ref_id=call.id,
                span=(0, 1),
                snippet_sha256="0" * 64,
            ),
        ],
    )
    assert claim.id is not None
    claim_id = claim.id

    events = [
        StepStartedEvent(
            idx=0, kind=TraceEventKind.step_started, step_id=understand_id
        ),
        StepFinishedEvent(
            idx=1,
            kind=TraceEventKind.step_finished,
            step_id=understand_id,
            output=UnderstandOutput(
                kind="understand",
                normalized_question="x",
                assumptions=[],
                task_type="generic",
            ),
        ),
        StepStartedEvent(idx=2, kind=TraceEventKind.step_started, step_id=gather_id),
        ToolCalledEvent(
            idx=3, kind=TraceEventKind.tool_called, step_id=gather_id, tool_call=call
        ),
        ToolReturnedEvent(
            idx=4, kind=TraceEventKind.tool_returned, step_id=gather_id, tool_result=res
        ),
        EvidenceRegisteredEvent(
            idx=5,
            kind=TraceEventKind.evidence_registered,
            step_id=gather_id,
            evidence=ev_ref,
        ),
        StepFinishedEvent(
            idx=6,
            kind=TraceEventKind.step_finished,
            step_id=gather_id,
            output=GatherOutput(kind="gather", evidence_refs=[ev_ref.id]),
        ),
        StepStartedEvent(idx=7, kind=TraceEventKind.step_started, step_id=derive_id),
        ClaimEmittedEvent(idx=8, kind=TraceEventKind.claim_emitted, claim=claim),
        StepFinishedEvent(
            idx=9,
            kind=TraceEventKind.step_finished,
            step_id=derive_id,
            output=DeriveOutput(kind="derive", emitted_claim_ids=[claim_id]),
        ),
        StepStartedEvent(idx=10, kind=TraceEventKind.step_started, step_id=verify_id),
        StepFinishedEvent(
            idx=11,
            kind=TraceEventKind.step_finished,
            step_id=verify_id,
            output=VerifyOutput(
                kind="verify",
                validated_claim_ids=[],
                rejected_claim_ids=[],
                insufficient_support=[],
            ),
        ),
        StepStartedEvent(idx=12, kind=TraceEventKind.step_started, step_id=finalize_id),
        StepFinishedEvent(
            idx=13,
            kind=TraceEventKind.step_finished,
            step_id=finalize_id,
            output=FinalizeOutput(kind="finalize", final_claim_ids=[claim_id]),
            ),
        ]

    trace = Trace(
        spec_id=spec_id,
        plan_id=plan_id,
        events=events,
        metadata={
            "seed": 0,
            "reasoning_policy": {"min_supports_per_claim": 1},
            "reasoning_trace": {
                "result_sha256": "0" * 64,
                "reasoning_trace_sha256": "0" * 64,
            },
        },
    )
    assert trace.id is not None
    report = verify_trace(trace=trace, plan=plan)
    assert report.summary_metrics["checks_failed"] == 0
    assert report.failures == []


def test_verifier_fails_on_missing_tool_result() -> None:
    spec = ProblemSpec(description="x", constraints={}, expected={})
    n1 = PlanNode(
        kind="gather", dependencies=[], step=StepSpec(kind="gather"), parameters={}
    )
    assert spec.id is not None
    assert n1.id is not None
    n1_id = n1.id
    spec_id = spec.id
    plan = Plan(spec_id=spec_id, nodes=[n1])
    assert plan.id is not None
    plan_id = plan.id

    call = ToolCall(step_id=n1_id, call_idx=0, tool_name="retrieve", arguments={})
    assert call.id is not None
    events = [
        StepStartedEvent(idx=0, kind=TraceEventKind.step_started, step_id=n1_id),
        ToolCalledEvent(
            idx=1, kind=TraceEventKind.tool_called, step_id=n1_id, tool_call=call
        ),
        StepFinishedEvent(
            idx=2,
            kind=TraceEventKind.step_finished,
            step_id=n1_id,
            output=GatherOutput(kind="gather", evidence_refs=[]),
        ),
    ]
    trace = Trace(spec_id=spec_id, plan_id=plan_id, events=events, metadata={})
    assert trace.id is not None

    report = verify_trace(trace=trace, plan=plan)
    assert report.summary_metrics["checks_failed"] >= 1
    assert any("tool_linkage" in f for f in report.failures)


def test_verifier_fails_on_unknown_claim_ref() -> None:
    spec = ProblemSpec(description="x", constraints={}, expected={})
    n1 = PlanNode(
        kind="derive", dependencies=[], step=StepSpec(kind="derive"), parameters={}
    )
    assert spec.id is not None
    assert n1.id is not None
    n1_id = n1.id
    spec_id = spec.id
    plan = Plan(spec_id=spec_id, nodes=[n1])
    assert plan.id is not None
    plan_id = plan.id

    claim = Claim(
        claim_type=ClaimType.derived,
        statement="x=1",
        structured={"x": 1},
        status=ClaimStatus.proposed,
        confidence=1.0,
        support_refs=[
            SupportRef(
                kind=SupportKind.tool_call,
                ref_id="nonexistent",
                span=(0, 1),
                snippet_sha256="0" * 64,
            )
        ],
    )
    assert claim.id is not None
    claim_id = claim.id
    events = [
        StepStartedEvent(idx=0, kind=TraceEventKind.step_started, step_id=n1_id),
        ClaimEmittedEvent(idx=1, kind=TraceEventKind.claim_emitted, claim=claim),
        StepFinishedEvent(
            idx=2,
            kind=TraceEventKind.step_finished,
            step_id=n1_id,
            output=DeriveOutput(kind="derive", emitted_claim_ids=[claim_id]),
        ),
    ]
    trace = Trace(spec_id=spec_id, plan_id=plan_id, events=events, metadata={})
    assert trace.id is not None

    report = verify_trace(trace=trace, plan=plan)
    assert any("claim_justifications" in f for f in report.failures)
