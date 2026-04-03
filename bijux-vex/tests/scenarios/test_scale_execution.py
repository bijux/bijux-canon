# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.execution_intent import ExecutionIntent

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.types import ExecutionArtifact, ExecutionRequest
from bijux_vex.domain.execution_requests.execute import (
    execute_request,
    start_execution_session,
)
from tests.fixtures.test_scale_vectors import build_scale_backend


def test_scale_execution_topk():
    backend = build_scale_backend(count=10000, dim=8)
    artifact = ExecutionArtifact(
        artifact_id="art-scale",
        corpus_fingerprint="corp",
        vector_fingerprint="vec",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.DETERMINISTIC,
    )
    with backend.tx_factory() as tx:
        backend.stores.ledger.put_artifact(tx, artifact)
    request = ExecutionRequest(
        request_id="scale-req",
        text=None,
        vector=tuple(0.0 for _ in range(8)),
        top_k=5,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
        execution_mode=ExecutionMode.STRICT,
    )
    session = start_execution_session(artifact, request, backend.stores)
    execution_result, results = execute_request(session, backend.stores)
    assert len(tuple(results)) == 5
    assert execution_result.cost.vector_reads >= 5
