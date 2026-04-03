# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import pytest

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import InvariantError
from bijux_vex.core.runtime.execution_plan import ExecutionPlan, RandomnessSource


def test_plan_fingerprint_is_stable():
    plan = ExecutionPlan(
        algorithm="algo",
        contract=ExecutionContract.DETERMINISTIC,
        k=3,
        scoring_fn="l2",
        randomness_sources=(
            RandomnessSource(name="seed", description="seed", category="sampling"),
        ),
        reproducibility_bounds="stable",
        steps=("a", "b"),
    )
    assert isinstance(plan.fingerprint, str)
    assert plan.fingerprint


def test_plan_requires_contract_enum():
    with pytest.raises(InvariantError):
        ExecutionPlan(
            algorithm="algo",
            contract="deterministic",  # type: ignore[arg-type]
            k=1,
            scoring_fn="l2",
        )
