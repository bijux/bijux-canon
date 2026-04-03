# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.runtime.vector_execution import RandomnessProfile
from bijux_vex.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    ExecutionBudget,
    ExecutionRequest,
    NDSettings,
    Vector,
)
from bijux_vex.domain.execution_requests.execute import (
    execute_request,
    start_execution_session,
)
from bijux_vex.infra.adapters.memory.backend import memory_backend


def test_nd_approximation_metrics_include_witness() -> None:
    backend = memory_backend()
    ann_runner = backend.ann
    assert ann_runner is not None
    with backend.tx_factory() as tx:
        doc = Document(document_id="doc-1", text="hello")
        chunk = Chunk(
            chunk_id="chunk-1", document_id=doc.document_id, text=doc.text, ordinal=0
        )
        vec_a = Vector(
            vector_id="vec-a", chunk_id=chunk.chunk_id, values=(0.0, 0.0), dimension=2
        )
        vec_b = Vector(
            vector_id="vec-b", chunk_id=chunk.chunk_id, values=(1.0, 1.0), dimension=2
        )
        backend.stores.vectors.put_document(tx, doc)
        backend.stores.vectors.put_chunk(tx, chunk)
        backend.stores.vectors.put_vector(tx, vec_a)
        backend.stores.vectors.put_vector(tx, vec_b)
        backend.stores.ledger.put_artifact(
            tx,
            ExecutionArtifact(
                artifact_id="art-nd",
                corpus_fingerprint="corp",
                vector_fingerprint="vec",
                metric="l2",
                scoring_version="v1",
                execution_contract=ExecutionContract.NON_DETERMINISTIC,
                index_state="ready",
            ),
        )

    request = ExecutionRequest(
        request_id="req-nd",
        text=None,
        vector=(0.0, 0.0),
        top_k=2,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
        execution_mode=ExecutionMode.BOUNDED,
        execution_budget=ExecutionBudget(
            max_latency_ms=10, max_memory_mb=10, max_error=0.5
        ),
        nd_settings=NDSettings(
            witness_rate=1.0, witness_sample_k=1, build_on_demand=True
        ),
    )
    randomness = RandomnessProfile(seed=0, sources=("test",), bounded=True)
    artifact = backend.stores.ledger.get_artifact("art-nd")
    session = start_execution_session(
        artifact, request, backend.stores, randomness, ann_runner
    )
    result, _ = execute_request(session, backend.stores, ann_runner=ann_runner)

    assert result.approximation is not None
    assert result.approximation.rank_instability is not None
    assert result.approximation.distance_margin is not None
    assert result.approximation.similarity_entropy is not None
    assert result.approximation.witness_report is not None
