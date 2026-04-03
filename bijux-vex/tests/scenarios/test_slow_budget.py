# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.execution_intent import ExecutionIntent

import pytest

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import BudgetExceededError
from dataclasses import replace

from bijux_vex.core.types import ExecutionBudget, ExecutionRequest, NDSettings
from bijux_vex.domain.execution_requests.execute import (
    execute_request,
    start_execution_session,
)
from bijux_vex.infra.adapters.memory.backend import memory_backend
from tests.conformance.test_cross_backend_replay import _seed_backend


@pytest.mark.slow
def test_latency_budget_enforced_under_load():
    backend = memory_backend()
    artifact, request = _seed_backend(backend, "slow-")
    artifact = replace(
        artifact,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        artifact_id="slow-art-nd",
    )
    request = ExecutionRequest(
        request_id="slow-req",
        text=None,
        vector=request.vector,
        top_k=1,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
        execution_mode=ExecutionMode.BOUNDED,
        execution_budget=ExecutionBudget(
            max_latency_ms=1,
            max_memory_mb=1,
            max_error=0.1,
            max_vectors=0,
            max_ann_probes=1,
        ),
        nd_settings=NDSettings(build_on_demand=True),
    )
    with backend.tx_factory() as tx:
        backend.stores.ledger.put_artifact(tx, artifact)
    session = start_execution_session(
        artifact, request, backend.stores, ann_runner=backend.ann
    )
    result, _ = execute_request(session, backend.stores, ann_runner=backend.ann)
    assert result.status.name.lower() == "partial"
    assert result.failure_reason is not None
