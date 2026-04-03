# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi <bijan@bijux.io>
from __future__ import annotations

import json

from bijux_canon_index.interfaces.schemas.models import (
    ExecutionArtifactRequest,
    IngestRequest,
)
from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.execution_intent import ExecutionIntent
from bijux_canon_index.core.execution_mode import ExecutionMode
from bijux_canon_index.core.types import ExecutionRequest
from bijux_canon_index.domain.requests.execute import (
    execute_request,
    start_execution_session,
)
from bijux_canon_index.domain.provenance.lineage import explain_result
from bijux_canon_index.infra.adapters.memory.backend import memory_backend
from bijux_canon_index.application.engine import VectorExecutionEngine


def test_explain_provenance_key_order_is_stable() -> None:
    backend = memory_backend()
    engine = VectorExecutionEngine(backend=backend)
    engine.ingest(IngestRequest(documents=["alpha"], vectors=[[0.0, 0.0]]))
    engine.materialize(
        ExecutionArtifactRequest(execution_contract=ExecutionContract.DETERMINISTIC)
    )
    artifact = backend.stores.ledger.get_artifact("art-1")
    assert artifact is not None
    request = ExecutionRequest(
        request_id="prov-test",
        text=None,
        vector=(0.0, 0.0),
        top_k=1,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
        execution_mode=ExecutionMode.STRICT,
    )
    session = start_execution_session(
        artifact, request, backend.stores, ann_runner=backend.ann
    )
    _, results_iter = execute_request(session, backend.stores, ann_runner=backend.ann)
    target = next(iter(results_iter))
    explain = explain_result(target, backend.stores)
    expected_order = [
        "document",
        "chunk",
        "vector",
        "artifact",
        "metric",
        "score",
        "correlation_id",
        "execution_contract",
        "execution_contract_status",
        "replayable",
        "execution_id",
        "nondeterministic_sources",
        "lossy_dimensions",
        "embedding_source",
        "embedding_determinism",
        "embedding_seed",
        "embedding_model_version",
        "embedding_provider",
        "embedding_provider_version",
        "embedding_device",
        "embedding_dtype",
        "embedding_normalization",
        "vector_store_backend",
        "vector_store_uri_redacted",
        "vector_store_index_params",
        "vector_store_consistency",
        "determinism_fingerprint",
    ]
    assert list(explain.keys()) == expected_order
    # Stable serialization across platforms.
    json.dumps(explain, default=str, sort_keys=False)
