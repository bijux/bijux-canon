# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path
import hashlib

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


def test_reasoning_trace_hash_mismatch_fails(tmp_path: Path) -> None:
    ev_bytes = b"abc"
    sha = hashlib.sha256(ev_bytes[0:1]).hexdigest()
    ev_path = tmp_path / "evidence"
    ev_path.mkdir(parents=True, exist_ok=True)
    (ev_path / "ev1.txt").write_bytes(ev_bytes)

    spec = ProblemSpec(description="q", constraints={}, expected={})
    plan_nodes = [
        PlanNode(kind="understand", dependencies=[], parameters={}, step=StepSpec(kind="understand")),
        PlanNode(kind="gather", dependencies=[], parameters={}, step=StepSpec(kind="gather")),
        PlanNode(kind="derive", dependencies=[], parameters={}, step=StepSpec(kind="derive")),
        PlanNode(kind="verify", dependencies=[], parameters={}, step=StepSpec(kind="verify")),
        PlanNode(kind="finalize", dependencies=[], parameters={}, step=StepSpec(kind="finalize")),
    ]
    plan = Plan(spec_id=spec.id, nodes=plan_nodes)

    call = ToolCall(step_id=plan_nodes[1].id, call_idx=0, tool_name="retrieve", arguments={})
    tres = ToolResult(call_id=call.id, success=True, result={"ok": True}, error=None)
    ev_ref = EvidenceRef(
        uri="mem://ev1",
        sha256=hashlib.sha256(ev_bytes).hexdigest(),
        span=(0, len(ev_bytes)),
        chunk_id=hashlib.sha256(b"chunk").hexdigest(),
        content_path="evidence/ev1.txt",
    )
    support = SupportRef(
        kind=SupportKind.evidence,
        ref_id=ev_ref.id,
        span=(0, 1),
        snippet_sha256=sha,
    )
    claim = Claim(
        statement=f"answer [evidence:{ev_ref.id}:0-1:{sha}]",
        status=ClaimStatus.proposed,
        confidence=0.5,
        supports=[support],
        claim_type=ClaimType.derived,
        structured={"reasoner": {}, "result_sha256": "0" * 64},
    )

    events = [
        StepStartedEvent(idx=0, kind=TraceEventKind.step_started, step_id=plan_nodes[0].id),
        StepFinishedEvent(
            idx=1,
            kind=TraceEventKind.step_finished,
            step_id=plan_nodes[0].id,
            output=UnderstandOutput(kind="understand", normalized_question="q", assumptions=[]),
        ),
        StepStartedEvent(idx=2, kind=TraceEventKind.step_started, step_id=plan_nodes[1].id),
        ToolCalledEvent(
            idx=3, kind=TraceEventKind.tool_called, step_id=plan_nodes[1].id, tool_call=call
        ),
        ToolReturnedEvent(
            idx=4, kind=TraceEventKind.tool_returned, step_id=plan_nodes[1].id, tool_result=tres
        ),
        EvidenceRegisteredEvent(
            idx=5, kind=TraceEventKind.evidence_registered, step_id=plan_nodes[1].id, evidence=ev_ref
        ),
        StepFinishedEvent(
            idx=6,
            kind=TraceEventKind.step_finished,
            step_id=plan_nodes[1].id,
            output=GatherOutput(kind="gather", evidence_refs=[ev_ref.id]),
        ),
        StepStartedEvent(idx=7, kind=TraceEventKind.step_started, step_id=plan_nodes[2].id),
        ClaimEmittedEvent(idx=8, kind=TraceEventKind.claim_emitted, claim=claim),
        StepFinishedEvent(
            idx=9,
            kind=TraceEventKind.step_finished,
            step_id=plan_nodes[2].id,
            output=DeriveOutput(kind="derive", emitted_claim_ids=[claim.id]),
        ),
        StepStartedEvent(idx=10, kind=TraceEventKind.step_started, step_id=plan_nodes[3].id),
        StepFinishedEvent(
            idx=11,
            kind=TraceEventKind.step_finished,
            step_id=plan_nodes[3].id,
            output=VerifyOutput(
                kind="verify", validated_claim_ids=[], rejected_claim_ids=[], insufficient_support=[]
            ),
        ),
        StepStartedEvent(idx=12, kind=TraceEventKind.step_started, step_id=plan_nodes[4].id),
        StepFinishedEvent(
            idx=13,
            kind=TraceEventKind.step_finished,
            step_id=plan_nodes[4].id,
            output=FinalizeOutput(
                kind="finalize",
                final_claim_ids=[claim.id],
                final_answer=claim.statement,
                uncertainty=None,
            ),
        ),
    ]
    trace = Trace(
        id="trace-1",
        spec_id=spec.id,
        plan_id=plan.id,
        events=events,
        metadata={
            "reasoning_trace": {
                "question": "q",
                "evidence_ids": [ev_ref.id],
                "result_sha256": "1" * 64,  # mismatch
                "reasoning_trace_sha256": "1" * 64,
            }
        },
    )
    report = verify_trace(trace=trace, plan=plan, artifacts_dir=tmp_path)
    assert any("reasoning_trace" in f.message for f in report.failures)
