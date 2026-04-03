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


def test_replay_reports_mismatch():
    backend = memory_backend()
    doc = Document(document_id="doc-m", text="hello")
    chunk = Chunk(
        chunk_id="chunk-m", document_id=doc.document_id, text="hello", ordinal=0
    )
    vec = Vector(vector_id="vec-m", chunk_id=chunk.chunk_id, values=(1.0,), dimension=1)
    art = ExecutionArtifact(
        artifact_id="art-m",
        corpus_fingerprint="corp",
        vector_fingerprint="vec",
        metric="l2",
        scoring_version="v1",
        build_params=(),
        execution_contract=ExecutionContract.DETERMINISTIC,
    )
    query = ExecutionRequest(
        request_id="q-m",
        text=None,
        vector=(0.0,),
        top_k=1,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
    )

    with backend.tx_factory() as tx:
        backend.stores.vectors.put_document(tx, doc)
        backend.stores.vectors.put_chunk(tx, chunk)
        backend.stores.vectors.put_vector(tx, vec)
        backend.stores.ledger.put_artifact(tx, art)

    from bijux_vex.domain.execution_requests.execute import (
        execute_request,
        start_execution_session,
    )

    session = start_execution_session(art, query, backend.stores)
    exec_result, _ = execute_request(session, backend.stores)
    with backend.tx_factory() as tx:
        backend.stores.ledger.put_execution_result(tx, exec_result)
    first = replay(
        query, art, backend.stores, baseline_fingerprint=exec_result.signature
    )

    # mutate vector to force mismatch
    with backend.tx_factory() as tx:
        backend.stores.vectors.put_vector(
            tx,
            Vector(
                vector_id="vec-m", chunk_id=chunk.chunk_id, values=(2.0,), dimension=1
            ),
        )

    second = replay(
        query,
        art,
        backend.stores,
        baseline_fingerprint=first.replay_fingerprint,
    )
    assert not second.matches
    assert "results_fingerprint" in second.details
