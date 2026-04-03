# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import hashlib
from pathlib import Path

from bijux_rar.core.rar_types import (
    Claim,
    ClaimEmittedEvent,
    ClaimStatus,
    ClaimType,
    EvidenceRef,
    EvidenceRegisteredEvent,
    Plan,
    PlanNode,
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
    VerificationPolicyMode,
)
from bijux_rar.rar.verification.verifier import verify_trace


def _build_minimal_plan(plan_id: str, spec_id: str) -> Plan:
    node = PlanNode(
        id="s1",
        kind="derive",
        dependencies=[],
        step=StepSpec(kind="derive"),
        parameters={},
    )
    return Plan(id=plan_id, spec_id=spec_id, nodes=[node], edges=[]).with_content_id()


def _build_trace_with_evidence(run_dir: Path, plan_id: str) -> Trace:
    ev_bytes = b"forged-evidence"
    ev_span = (0, len(ev_bytes))
    evidence_path = run_dir / "evidence" / "ev1.txt"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_bytes(ev_bytes)

    ev_ref = EvidenceRef.model_validate(
        {
            "id": "ev1",
            "uri": "mem://doc1",
            "sha256": "0" * 64,  # intentionally wrong to trigger failure
            "span": ev_span,
            # arbitrary but valid-looking chunk id (hex-64)
            "chunk_id": "a" * 64,
            "content_path": evidence_path.relative_to(run_dir).as_posix(),
        }
    )
    call = ToolCall(
        id="call1",
        tool_name="retrieve",
        arguments={},
        step_id="s1",
        call_idx=0,
    )
    res = ToolResult(call_id="call1", success=True, result={"ok": True})
    snippet_hash = hashlib.sha256(ev_bytes[ev_span[0] : ev_span[1]]).hexdigest()
    claim = Claim(
        id="c1",
        statement=f"claim [evidence:{ev_ref.id}:{ev_span[0]}-{ev_span[1]}:{snippet_hash}]",
        status=ClaimStatus.proposed,
        confidence=1.0,
        supports=[
            SupportRef(
                kind=SupportKind.evidence,
                ref_id=ev_ref.id,
                span=ev_span,
                snippet_sha256=snippet_hash,
            )
        ],
        claim_type=ClaimType.derived,
    )
    events = [
        StepStartedEvent(idx=0, kind=TraceEventKind.step_started, step_id="s1"),
        ToolCalledEvent(idx=1, kind=TraceEventKind.tool_called, step_id="s1", call=call),
        ToolReturnedEvent(idx=2, kind=TraceEventKind.tool_returned, step_id="s1", result=res),
        EvidenceRegisteredEvent(idx=3, kind=TraceEventKind.evidence_registered, step_id="s1", evidence=ev_ref),
        ClaimEmittedEvent(idx=4, kind=TraceEventKind.claim_emitted, step_id="s1", claim=claim),
        StepFinishedEvent(
            idx=5,
            kind=TraceEventKind.step_finished,
            step_id="s1",
            output={"kind": "derive", "claim_ids": [claim.id]},
        ),
    ]
    trace = Trace(
        spec_id="spec1",
        plan_id=plan_id,
        events=events,
        metadata={},
    ).with_content_id()
    return trace


def test_forged_evidence_hash_fails(tmp_path: Path) -> None:
    plan = _build_minimal_plan(plan_id="plan1", spec_id="spec1")
    trace = _build_trace_with_evidence(tmp_path, plan_id=plan.id)
    report = verify_trace(
        trace=trace,
        plan=plan,
        artifacts_dir=tmp_path,
        policy=VerificationPolicyMode.strict,
    )
    messages = {f.invariant_id for f in report.failures}
    assert "INV-EVD-001" in messages, f"expected evidence invariant failure, got {messages}"
