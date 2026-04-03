# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_rar.core.rar_types import (
    Claim,
    ClaimStatus,
    ClaimType,
    EvidenceRef,
    Plan,
    PlanNode,
    ProblemSpec,
    StepSpec,
    ToolCall,
)


def test_problem_spec_id_is_content_addressed() -> None:
    s1 = ProblemSpec(description="A", constraints={"k": "v"})
    s2 = ProblemSpec(description="A", constraints={"k": "v"})
    assert s1.id == s2.id


def test_plan_node_id_is_content_addressed() -> None:
    spec = StepSpec(kind="understand")
    n1 = PlanNode(kind="understand", dependencies=["x"], step=spec, parameters={"p": 1})
    n2 = PlanNode(kind="understand", dependencies=["x"], step=spec, parameters={"p": 1})
    assert n1.id == n2.id
    assert n1.id is not None


def test_plan_id_is_content_addressed() -> None:
    spec = ProblemSpec(description="A")
    n1 = PlanNode(kind="understand", dependencies=[], step=StepSpec(kind="understand"))
    assert n1.id is not None
    n2 = PlanNode(kind="derive", dependencies=[n1.id], step=StepSpec(kind="derive"))
    assert spec.id is not None
    plan1 = Plan(spec_id=spec.id, nodes=[n1, n2])
    plan2 = Plan(spec_id=spec.id, nodes=[n1, n2])
    assert plan1.id == plan2.id


def test_tool_call_and_claim_ids_set() -> None:
    node = PlanNode(
        kind="understand", dependencies=[], step=StepSpec(kind="understand")
    )
    assert node.id is not None
    call = ToolCall(step_id=node.id, call_idx=0, tool_name="demo")
    claim = Claim(
        claim_type=ClaimType.derived,
        statement="ok",
        structured={"ok": True},
        status=ClaimStatus.proposed,
        confidence=1.0,
    )
    evidence = EvidenceRef(
        uri="file://x", sha256="0" * 64, span=(0, 1), chunk_id="0" * 64
    )
    assert call.id is not None
    assert claim.id is not None
    assert evidence.id is not None
