# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_canon_index.core.compliance import ComparisonPolicy, enforce_policy
from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.errors import InvariantError
from bijux_canon_index.core.execution_result import ExecutionCost, ExecutionResult
from bijux_canon_index.core.runtime.execution_plan import ExecutionPlan
from bijux_canon_index.domain.requests.execution_diff import VectorExecutionDiff
import pytest


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
