# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.execution_intent import ExecutionIntent

from dataclasses import replace

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.contracts.performance_contracts import assert_performance_envelope
from bijux_vex.domain.execution_requests.execute import (
    execute_request,
    start_execution_session,
)
from bijux_vex.infra.adapters.ann_reference import ReferenceAnnRunner
from bijux_vex.infra.adapters.memory.backend import memory_backend
from bijux_vex.core.types import ExecutionBudget, NDSettings
from tests.conformance.test_cross_backend_replay import _seed_backend


def test_deterministic_execution_respects_envelope():
    backend = memory_backend()
    artifact, request = _seed_backend(backend, "perf-")
    session = start_execution_session(artifact, request, backend.stores)
    result, _ = execute_request(session, backend.stores)
    assert_performance_envelope(result, ExecutionContract.DETERMINISTIC)


def test_nd_execution_requires_approximation_report():
    backend = memory_backend()
    artifact, request = _seed_backend(backend, "nd-")
    artifact = replace(
        artifact,
        artifact_id="nd-art-nd",
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
    )
    request = replace(
        request,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
        execution_mode=ExecutionMode.BOUNDED,
        execution_budget=ExecutionBudget(
            max_latency_ms=10, max_memory_mb=10, max_error=1.0
        ),
        nd_settings=NDSettings(
            build_on_demand=True,
            candidate_k=10,
            ef_search=128,
        ),
    )
    with backend.tx_factory() as tx:
        backend.stores.ledger.put_artifact(tx, artifact)
    backend = backend._replace(ann=ReferenceAnnRunner(backend.stores.vectors))
    session = start_execution_session(
        artifact, request, backend.stores, ann_runner=backend.ann
    )
    result, _ = execute_request(session, backend.stores, ann_runner=backend.ann)
    assert_performance_envelope(result, ExecutionContract.NON_DETERMINISTIC)
