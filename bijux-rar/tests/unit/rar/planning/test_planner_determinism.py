# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_rar.core.rar_types import ProblemSpec
from bijux_rar.rar.planning.planner import plan_problem


def test_planner_is_deterministic_same_input_same_plan_id() -> None:
    spec1 = ProblemSpec(
        description="x",
        constraints={"needs_retrieval": True, "query": "abc", "top_k": 2},
    )
    spec2 = ProblemSpec(
        description="x",
        constraints={"needs_retrieval": True, "query": "abc", "top_k": 2},
    )

    p1 = plan_problem(spec=spec1, preset="default")
    p2 = plan_problem(spec=spec2, preset="default")

    assert p1.id == p2.id
    assert [n.kind for n in p1.nodes] == [
        "understand",
        "gather",
        "derive",
        "verify",
        "finalize",
    ]
