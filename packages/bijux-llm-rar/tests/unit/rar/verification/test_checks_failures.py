# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_rar.core.rar_types import (
    EvidenceRef,
    EvidenceRegisteredEvent,
    Plan,
    PlanNode,
    StepFinishedEvent,
    StepSpec,
    Trace,
    TraceEventKind,
    VerifyOutput,
)
from bijux_rar.rar.verification.checks import VerificationContext, run_all_checks


def _plan_with_single_step() -> Plan:
    node = PlanNode(kind="verify", dependencies=[], step=StepSpec(kind="verify"))
    return Plan(spec_id="spec", nodes=[node])


def test_checks_fail_when_required_steps_missing() -> None:
    plan = _plan_with_single_step()
    trace = Trace(
        spec_id=plan.spec_id,
        plan_id=plan.id,
        events=[],
        metadata={},
    )
    ctx = VerificationContext(trace=trace, plan=plan, artifacts_dir=None)
    checks, failures = run_all_checks(ctx)
    assert any(c.name == "required_steps" and not c.passed for c in checks)
    assert failures


def test_evidence_hash_failure_detected(tmp_path) -> None:
    plan = _plan_with_single_step()
    ev_file = tmp_path / "ev.txt"
    ev_file.write_text("abc", encoding="utf-8")
    ev = EvidenceRef(
        uri="file://ev",
        sha256="0" * 64,  # wrong
        span=(0, 3),
        chunk_id="a" * 64,
        content_path=ev_file.name,
    )
    trace = Trace(
        spec_id=plan.spec_id,
        plan_id=plan.id,
        events=[
            EvidenceRegisteredEvent(
                idx=0,
                kind=TraceEventKind.evidence_registered,
                step_id=plan.nodes[0].id,
                evidence=ev,
            ),
            StepFinishedEvent(
                idx=1,
                kind=TraceEventKind.step_finished,
                step_id=plan.nodes[0].id,
                output=VerifyOutput(
                    kind="verify",
                    validated_claim_ids=[],
                    rejected_claim_ids=[],
                    insufficient_support=[],
                ),
            ),
        ],
        metadata={},
    )
    ctx = VerificationContext(trace=trace, plan=plan, artifacts_dir=tmp_path)
    checks, failures = run_all_checks(ctx)
    assert any(c.name == "evidence_hashes" and not c.passed for c in checks)
    assert failures
