# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_rar.core.fingerprints import fingerprint_obj
from bijux_rar.core.rar_types import ProblemSpec
from bijux_rar.rar.execution.executor import execute_plan
from bijux_rar.rar.execution.runtime import Runtime
from bijux_rar.rar.planning.planner import plan_problem


def test_executor_is_deterministic_same_plan_seed_same_trace_fp() -> None:
    spec = ProblemSpec(
        description="x",
        constraints={"needs_retrieval": True, "query": "abc", "top_k": 2},
    )
    plan = plan_problem(spec=spec, preset="default")

    r1 = Runtime.fake(seed=7)
    r2 = Runtime.fake(seed=7)

    t1 = execute_plan(plan=plan, runtime=r1)
    t2 = execute_plan(plan=plan, runtime=r2)

    fp1 = fingerprint_obj(t1.model_dump(mode="json"))
    fp2 = fingerprint_obj(t2.model_dump(mode="json"))
    assert fp1 == fp2
