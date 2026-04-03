# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import pytest

from bijux_vex.core.compliance import ComparisonPolicy, enforce_policy
from bijux_vex.domain.execution_requests.compare import VectorExecutionDiff
from bijux_vex.core.execution_result import ExecutionResult, ExecutionCost
from bijux_vex.core.types import Result
from bijux_vex.core.runtime.execution_plan import ExecutionPlan
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import InvariantError


def _dummy_execution(exec_id: str) -> ExecutionResult:
    plan = ExecutionPlan(
        algorithm="exact_vector_execution",
        contract=ExecutionContract.DETERMINISTIC,
        k=1,
        scoring_fn="l2",
        randomness_sources=(),
        reproducibility_bounds="bit-identical",
        steps=("step",),
    )
    return ExecutionResult(
        execution_id=exec_id,
        signature=exec_id,
        artifact_id="a",
        plan=plan,
        results=(),
        cost=ExecutionCost(0, 0, 0, 0.0),
    )


def test_comparison_policy_enforced():
    diff = VectorExecutionDiff(
        execution_a=_dummy_execution("a"),
        execution_b=_dummy_execution("b"),
        overlap_ratio=1.0,
        recall_delta=0.0,
        rank_instability=0.1,
    )
    policy = ComparisonPolicy(min_recall=0.0, max_rank_instability=0.5)
    enforce_policy(diff, policy)

    bad_policy = ComparisonPolicy(min_recall=0.0, max_rank_instability=0.05)
    with pytest.raises(InvariantError):
        enforce_policy(diff, bad_policy)
