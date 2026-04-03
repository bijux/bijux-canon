# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_rar.core.invariants import (
    validate_plan,
    validate_trace,
    validate_verification_report,
)
from bijux_rar.core.rar_types import (
    DeriveOutput,
    EvidenceRef,
    Plan,
    PlanNode,
    ProblemSpec,
    StepFinishedEvent,
    StepSpec,
    StepStartedEvent,
    ToolCall,
    ToolCalledEvent,
    Trace,
    TraceEventKind,
    VerificationCheck,
    VerificationReport,
)


def test_plan_cycle_detected() -> None:
    spec = ProblemSpec(description="Cycle test")
    a = PlanNode(kind="understand", dependencies=[], step=StepSpec(kind="understand"))
    assert a.id is not None
    b = PlanNode(kind="derive", dependencies=[a.id], step=StepSpec(kind="derive"))
    assert b.id is not None
    a2 = PlanNode(
        id=a.id, kind=a.kind, dependencies=[b.id], step=a.step, parameters=a.parameters
    )

    assert spec.id is not None
    plan = Plan(spec_id=spec.id, nodes=[a2, b])
    errs = validate_plan(plan)
    assert any("cycle" in e.lower() for e in errs)


def test_plan_validates_dependencies_and_ids() -> None:
    spec = ProblemSpec(description="Valid plan")
    n1 = PlanNode(kind="understand", dependencies=[], step=StepSpec(kind="understand"))
    assert spec.id is not None
    assert n1.id is not None
    plan = Plan(spec_id=spec.id, nodes=[n1])
    errs = validate_plan(plan)
    assert errs == []


def test_trace_invariants_missing_tool_result_and_ordering() -> None:
    spec = ProblemSpec(description="Trace invariants")
    node = PlanNode(kind="derive", dependencies=[], step=StepSpec(kind="derive"))
    assert spec.id is not None
    assert node.id is not None
    plan = Plan(spec_id=spec.id, nodes=[node])

    tcall = ToolCall(step_id=node.id, call_idx=0, tool_name="demo")
    evs = [
        StepStartedEvent(idx=1, kind=TraceEventKind.step_started, step_id=node.id),
        ToolCalledEvent(
            idx=0, kind=TraceEventKind.tool_called, step_id=node.id, tool_call=tcall
        ),
        StepFinishedEvent(
            idx=2,
            kind=TraceEventKind.step_finished,
            step_id=node.id,
            output=DeriveOutput(kind="derive", emitted_claim_ids=[]),
        ),
    ]
    assert plan.id is not None
    trace = Trace(spec_id=spec.id, plan_id=plan.id, events=evs)

    errs = validate_trace(trace, plan)
    assert any("idx must be monotonically" in e for e in errs)
    assert any("Missing tool results" in e for e in errs)


def test_trace_invariants_evidence_must_be_referenced() -> None:
    spec = ProblemSpec(description="Evidence invariant")
    node = PlanNode(kind="derive", dependencies=[], step=StepSpec(kind="derive"))
    assert spec.id is not None
    assert node.id is not None
    plan = Plan(spec_id=spec.id, nodes=[node])

    evidence = EvidenceRef(
        uri="file://x", sha256="0" * 64, span=(0, 1), chunk_id="0" * 64
    )
    from bijux_rar.core.rar_types import EvidenceRegisteredEvent

    evs = [
        StepStartedEvent(idx=0, kind=TraceEventKind.step_started, step_id=node.id),
        EvidenceRegisteredEvent(
            idx=1,
            kind=TraceEventKind.evidence_registered,
            evidence=evidence,
            step_id=node.id,
        ),
        StepFinishedEvent(
            idx=2,
            kind=TraceEventKind.step_finished,
            step_id=node.id,
            output=DeriveOutput(kind="derive", emitted_claim_ids=[]),
        ),
    ]
    assert plan.id is not None
    trace = Trace(spec_id=spec.id, plan_id=plan.id, events=evs)
    errs = validate_trace(trace, plan)
    assert errs == []


def test_verification_report_duplicates_and_failures() -> None:
    checks = [
        VerificationCheck(name="a", passed=True),
        VerificationCheck(name="a", passed=True),
    ]
    report = VerificationReport(trace_id="t", checks=checks, failures=["x"])
    errs = validate_verification_report(report)
    assert any("duplicate" in e.lower() for e in errs)
