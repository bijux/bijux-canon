# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.execution_intent import ExecutionIntent

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    ExecutionRequest,
    Vector,
)
from bijux_vex.domain.provenance.replay import replay
from bijux_vex.infra.adapters.memory.backend import memory_backend


def test_replay_produces_identical_fingerprint():
    backend = memory_backend()
    doc = Document(document_id="doc-r", text="hello")
    chunk = Chunk(
        chunk_id="chunk-r", document_id=doc.document_id, text="hello", ordinal=0
    )
    vector = Vector(
        vector_id="vec-r", chunk_id=chunk.chunk_id, values=(0.0, 0.0), dimension=2
    )
    artifact = ExecutionArtifact(
        artifact_id="art-r",
        corpus_fingerprint="corp",
        vector_fingerprint="vec",
        metric="l2",
        scoring_version="v1",
        build_params=(),
        execution_contract=ExecutionContract.DETERMINISTIC,
    )
    query = ExecutionRequest(
        request_id="q-r",
        text=None,
        vector=(0.0, 0.0),
        top_k=1,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
    )

    with backend.tx_factory() as tx:
        backend.stores.vectors.put_document(tx, doc)
        backend.stores.vectors.put_chunk(tx, chunk)
        backend.stores.vectors.put_vector(tx, vector)
        backend.stores.ledger.put_artifact(tx, artifact)

    from bijux_vex.domain.execution_requests.execute import (
        execute_request,
        start_execution_session,
    )

    session = start_execution_session(artifact, query, backend.stores)
    first_result, _ = execute_request(session, backend.stores)
    with backend.tx_factory() as tx:
        backend.stores.ledger.put_execution_result(tx, first_result)
    from bijux_vex.domain.provenance.replay import _results_fingerprint

    baseline_fp = _results_fingerprint(first_result.results)
    first = replay(query, artifact, backend.stores, baseline_fingerprint=baseline_fp)
    second = replay(
        query, artifact, backend.stores, baseline_fingerprint=first.replay_fingerprint
    )

    assert first.matches
    assert second.matches
    assert first.replay_fingerprint == second.replay_fingerprint
