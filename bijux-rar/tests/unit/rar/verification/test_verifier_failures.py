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
    DeriveOutput,
    EvidenceRef,
    EvidenceRegisteredEvent,
    Plan,
    PlanNode,
    ProblemSpec,
    StepFinishedEvent,
    StepSpec,
    StepStartedEvent,
    SupportKind,
    SupportRef,
    Trace,
    TraceEventKind,
)
from bijux_rar.rar.verification.verifier import verify_trace


def _build_minimal_plan() -> Plan:
    spec = ProblemSpec(description="x")
    n = PlanNode(kind="derive", dependencies=[], step=StepSpec(kind="derive"))
    return Plan(spec_id=spec.id, nodes=[n])


def test_verifier_fails_on_hash_mismatch(tmp_path: Path) -> None:
    plan = _build_minimal_plan()
    ev_path = tmp_path / "evidence" / "ev.txt"
    ev_path.parent.mkdir(parents=True, exist_ok=True)
    ev_path.write_text("hello", encoding="utf-8")
    wrong_sha = hashlib.sha256(b"bye").hexdigest()

    ev_ref = EvidenceRef(
        id="ev1",
        uri="file://ev",
        sha256=wrong_sha,
        span=(0, 5),
        chunk_id="a" * 64,
        content_path=ev_path.relative_to(tmp_path).as_posix(),
    )
    claim = Claim(
        claim_type=ClaimType.derived,
        statement=f"x [evidence:ev1:0-5:{wrong_sha}]",
        status=ClaimStatus.proposed,
        confidence=1.0,
        supports=[
            SupportRef(
                kind=SupportKind.evidence,
                ref_id=ev_ref.id,
                span=(0, 5),
                snippet_sha256=wrong_sha,
            )
        ],
    )
    events = [
        StepStartedEvent(idx=0, kind=TraceEventKind.step_started, step_id=plan.nodes[0].id),
        EvidenceRegisteredEvent(
            idx=1,
            kind=TraceEventKind.evidence_registered,
            step_id=plan.nodes[0].id,
            evidence=ev_ref,
        ),
        ClaimEmittedEvent(idx=2, kind=TraceEventKind.claim_emitted, claim=claim),
        StepFinishedEvent(
            idx=3,
            kind=TraceEventKind.step_finished,
            step_id=plan.nodes[0].id,
            output=DeriveOutput(kind="derive", emitted_claim_ids=[claim.id]),
        ),
    ]
    trace = Trace(spec_id=plan.spec_id, plan_id=plan.id, events=events, metadata={})

    report = verify_trace(trace=trace, plan=plan, artifacts_dir=tmp_path)
    assert report.failures, "expected failures for hash mismatch"
    assert any("sha256 mismatch" in f.message for f in report.failures)


def test_verifier_rejects_span_out_of_bounds(tmp_path: Path) -> None:
    plan = _build_minimal_plan()
    ev_path = tmp_path / "evidence" / "ev.txt"
    ev_path.parent.mkdir(parents=True, exist_ok=True)
    data = b"abc"
    ev_path.write_bytes(data)
    sha = hashlib.sha256(data).hexdigest()

    ev_ref = EvidenceRef(
        id="ev1",
        uri="file://ev",
        sha256=sha,
        span=(0, len(data)),
        chunk_id="a" * 64,
        content_path=ev_path.relative_to(tmp_path).as_posix(),
    )
    # span points beyond evidence length
    bad_span = (0, len(data) + 5)
    claim = Claim(
        claim_type=ClaimType.derived,
        statement=f"x [evidence:ev1:{bad_span[0]}-{bad_span[1]}:{sha}]",
        status=ClaimStatus.proposed,
        confidence=1.0,
        supports=[
            SupportRef(
                kind=SupportKind.evidence,
                ref_id=ev_ref.id,
                span=bad_span,
                snippet_sha256=sha,
            )
        ],
    )
    events = [
        EvidenceRegisteredEvent(
            idx=0,
            kind=TraceEventKind.evidence_registered,
            step_id=plan.nodes[0].id,
            evidence=ev_ref,
        ),
        ClaimEmittedEvent(idx=1, kind=TraceEventKind.claim_emitted, claim=claim),
    ]
    trace = Trace(spec_id=plan.spec_id, plan_id=plan.id, events=events, metadata={})

    report = verify_trace(trace=trace, plan=plan, artifacts_dir=tmp_path)
    assert report.failures
