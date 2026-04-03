# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import pytest

from bijux_rar.core.rar_types import Plan, PlanNode, StepSpec
from bijux_rar.rar.execution.executor import _topo


def test_cycle_detected_fail_fast() -> None:
    n1 = PlanNode(id="n1", kind="gather", dependencies=["n2"], step=StepSpec(kind="gather"))
    n2 = PlanNode(id="n2", kind="derive", dependencies=["n1"], step=StepSpec(kind="derive"))
    plan = Plan(spec_id="spec", nodes=[n1, n2], edges=[("n1", "n2"), ("n2", "n1")])
    with pytest.raises(RuntimeError) as exc:
        _topo(plan)
    assert "INV-ORD-001" in str(exc.value)


def test_missing_dependency_edge_fail_fast() -> None:
    n1 = PlanNode(id="n1", kind="gather", dependencies=[], step=StepSpec(kind="gather"))
    n2 = PlanNode(id="n2", kind="derive", dependencies=["n1"], step=StepSpec(kind="derive"))
    # Edge list is optional; should not raise if dependencies are consistent.
    plan = Plan(spec_id="spec", nodes=[n1, n2], edges=[])
    ordering = _topo(plan)
    assert [n.id for n in ordering] == ["n1", "n2"]


def test_edge_points_to_unknown_node() -> None:
    n1 = PlanNode(id="n1", kind="gather", dependencies=[], step=StepSpec(kind="gather"))
    plan = Plan(spec_id="spec", nodes=[n1], edges=[("n1", "nX")])
    with pytest.raises(RuntimeError) as exc:
        _topo(plan)
    assert "INV-ORD-001" in str(exc.value)
