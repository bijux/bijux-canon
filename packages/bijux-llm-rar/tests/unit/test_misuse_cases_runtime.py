# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

from bijux_rar.boundaries.serde.trace_jsonl import write_trace_jsonl
from bijux_rar.core.invariants import validate_trace
from bijux_rar.core.rar_types import (
    Claim,
    ClaimStatus,
    ClaimType,
    EvidenceRef,
    ClaimEmittedEvent,
    EvidenceRegisteredEvent,
    Plan,
    PlanNode,
    StepFinishedEvent,
    StepStartedEvent,
    StepSpec,
    SupportKind,
    SupportRef,
    ToolCall,
    ToolResult,
    Trace,
    ToolCalledEvent,
    ToolReturnedEvent,
)
from bijux_rar.rar.verification.verifier import verify_trace


def _fake_plan() -> Plan:
    n1 = PlanNode(kind="understand", dependencies=[], step=StepSpec(kind="understand"))
    n2 = PlanNode(kind="derive", dependencies=[n1.id], step=StepSpec(kind="derive"))
    return Plan(spec_id="spec1", nodes=[n1, n2], edges=[(n1.id, n2.id)])


def _fake_trace(schema_version: int = 1) -> tuple[Trace, Plan]:
    plan = _fake_plan()
    ev = EvidenceRef(
        id="ev1",
        uri="mem://d1",
        sha256="0" * 64,
        span=(0, 1),
        content_path="",
        chunk_id="0" * 64,
    )
    call = ToolCall(
        id="call1",
        tool_name="retrieve",
        arguments={},
        step_id="s1",
        call_idx=0,
    )
    res = ToolResult(call_id="call1", success=True, result={"ok": True})
    claim = Claim(
        id="c1",
        statement="bad [evidence:ev1:0-1:ffff]",
        status=ClaimStatus.proposed,
        confidence=1.0,
        supports=[SupportRef(kind=SupportKind.evidence, ref_id=ev.id, span=(0, 1), snippet_sha256="0" * 64)],
        claim_type=ClaimType.derived,
    )
    events = [
        StepStartedEvent(idx=0, step_id="s1"),
        ToolCalledEvent(idx=1, step_id="s1", call=call),
        ToolReturnedEvent(idx=2, step_id="s1", result=res),
        EvidenceRegisteredEvent(idx=3, step_id="s1", evidence=ev),
        ClaimEmittedEvent(idx=4, step_id="s1", claim=claim),
        StepFinishedEvent(idx=5, step_id="s1", output={"kind": "derive", "claim_ids": ["c1"]}),
    ]
    return Trace(
        id="t1",
        spec_id="spec1",
        plan_id=plan.id,
        events=events,
        metadata={},
        schema_version=schema_version,
        runtime_protocol_version=1,
        canonicalization_version=1,
        fingerprint_algo="sha256",
    ), plan


def test_misuse_invalid_schema_version(tmp_path: Path) -> None:
    tr, plan = _fake_trace(schema_version=999)
    errors = validate_trace(tr, plan=plan)
    assert errors, "unsupported schema_version should raise validation errors"


def test_misuse_span_hash_mismatch(tmp_path: Path) -> None:
    tr, plan = _fake_trace(schema_version=1)
    trace_path = tmp_path / "trace.jsonl"
    write_trace_jsonl(tr, trace_path)
    report = verify_trace(trace=tr, plan=plan)
    assert report.failures, "span/hash mismatch must be rejected"
