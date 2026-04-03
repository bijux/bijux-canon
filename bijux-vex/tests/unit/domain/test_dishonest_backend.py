# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_vex.contracts.resources import (
    BackendCapabilities,
    ExecutionLedger,
    ExecutionResources,
    VectorSource,
)
from bijux_vex.contracts.tx import Tx
from bijux_vex.contracts.authz import AllowAllAuthz
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import NDExecutionUnavailableError
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.runtime.execution_plan import ExecutionPlan
from bijux_vex.core.runtime.vector_execution import RandomnessProfile, VectorExecution
from bijux_vex.core.types import ExecutionArtifact, ExecutionBudget, ExecutionRequest
from bijux_vex.domain.execution_requests.plan import run_plan
from bijux_vex.infra.adapters.memory.backend import (
    MemoryExecutionLedger,
    MemoryState,
    MemoryVectorSource,
)


def test_backend_claims_ann_support_but_runner_missing():
    # Backend advertises ANN capability but provides no runner → must raise structured ND error.
    state = MemoryState()
    vectors = MemoryVectorSource(state)
    ledger: ExecutionLedger = MemoryExecutionLedger(state)
    resources = ExecutionResources(
        name="dishonest-memory",
        vectors=vectors,
        ledger=ledger,
        capabilities=BackendCapabilities(
            contracts={
                ExecutionContract.DETERMINISTIC,
                ExecutionContract.NON_DETERMINISTIC,
            },
            max_vector_size=1024,
            metrics={"l2"},
            deterministic_query=True,
            replayable=True,
            isolation_level="process",
            ann_support=True,
            supports_ann=True,
        ),
    )
    artifact = ExecutionArtifact(
        artifact_id="art",
        corpus_fingerprint="corp",
        vector_fingerprint="vec",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
    )
    request = ExecutionRequest(
        request_id="req",
        text=None,
        vector=(0.0, 0.0),
        top_k=1,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
        execution_mode=ExecutionMode.BOUNDED,
        execution_budget=ExecutionBudget(
            max_latency_ms=1, max_memory_mb=1, max_error=0.1
        ),
    )
    plan = ExecutionPlan(
        algorithm="ann_approximate",
        contract=ExecutionContract.NON_DETERMINISTIC,
        k=request.top_k,
        scoring_fn=artifact.metric,
        randomness_sources=(),
        reproducibility_bounds="bounded",
        steps=("plan_nondeterministic", "execute_ann"),
    )
    randomness = RandomnessProfile(seed=1, sources=("ann",), bounded=True)
    execution = VectorExecution(
        request=request,
        contract=request.execution_contract,
        backend_id=resources.name,
        algorithm="ann_approximate",
        plan=plan,
        parameters=(("top_k", request.top_k),),
        randomness=randomness,
    )
    try:
        next(iter(run_plan(plan, execution, artifact, resources, ann_runner=None)))
        assert False, "run_plan should have failed without ANN runner"
    except NDExecutionUnavailableError as exc:
        assert exc.capability == "supports_ann"
        assert exc.retryable is False
