# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import pytest

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.runtime.execution_plan import ExecutionPlan
from bijux_vex.domain.execution_requests.plan import run_plan
from bijux_vex.infra.adapters.memory.backend import memory_backend
from bijux_vex.core.types import ExecutionArtifact, ExecutionRequest
from bijux_vex.core.errors import InvariantError


def test_plan_tampering_rejected():
    backend = memory_backend()
    with backend.tx_factory() as tx:
        backend.stores.ledger.put_artifact(
            tx,
            ExecutionArtifact(
                artifact_id="art",
                corpus_fingerprint="corp",
                vector_fingerprint="vec",
                metric="l2",
                scoring_version="v1",
                execution_contract=ExecutionContract.DETERMINISTIC,
            ),
        )
    plan = ExecutionPlan(
        algorithm="exact_vector_execution",
        contract=ExecutionContract.DETERMINISTIC,
        k=1,
        scoring_fn="l2",
        steps=("score",),
    )
    # tamper fingerprint
    object.__setattr__(plan, "fingerprint", "bogus")
    with pytest.raises(InvariantError):
        run_plan(
            plan,
            execution=type("E", (), {"contract": ExecutionContract.DETERMINISTIC}),
            artifact=backend.stores.ledger.get_artifact("art"),
            resources=backend.stores,
        )
