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
from bijux_vex.domain.provenance.lineage import explain_result
from bijux_vex.infra.adapters.memory.backend import memory_backend


def test_explain_reconstructs_full_chain():
    backend = memory_backend()
    doc = Document(document_id="doc", text="hello")
    chunk = Chunk(
        chunk_id="chunk", document_id=doc.document_id, text="hello", ordinal=0
    )
    vector = Vector(
        vector_id="vec", chunk_id=chunk.chunk_id, values=(0.0, 0.0), dimension=2
    )
    artifact = ExecutionArtifact(
        artifact_id="art",
        corpus_fingerprint="corp",
        vector_fingerprint="vec",
        metric="l2",
        scoring_version="v1",
        build_params=(),
        execution_contract=ExecutionContract.DETERMINISTIC,
    )
    query = ExecutionRequest(
        request_id="q",
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

    result = next(iter(backend.stores.vectors.query(artifact.artifact_id, query)))
    explanation = explain_result(result, backend.stores)

    assert explanation["document"] == doc
    assert explanation["chunk"] == chunk
    assert explanation["vector"] == vector
    assert explanation["artifact"] == artifact
    assert explanation["metric"] == artifact.metric
    assert explanation["score"] == result.score
    assert explanation["correlation_id"] == result.request_id
    assert explanation["execution_contract"] == artifact.execution_contract
    assert explanation["execution_contract_status"] == "stable"
    assert explanation["replayable"] is artifact.replayable
    assert explanation["execution_id"] == artifact.execution_id
    assert explanation["nondeterministic_sources"] == ()
    assert explanation["lossy_dimensions"] == ()
    assert explanation["embedding_source"] is None
    assert explanation["embedding_determinism"] is None
    assert explanation["embedding_seed"] is None
    assert explanation["embedding_model_version"] is None
    assert explanation["embedding_provider"] is None
    assert explanation["embedding_provider_version"] is None
    assert explanation["embedding_device"] is None
    assert explanation["embedding_dtype"] is None
    assert explanation["embedding_normalization"] is None
    assert explanation["vector_store_backend"] is None
    assert explanation["vector_store_uri_redacted"] is None
    assert explanation["vector_store_index_params"] is None
    assert explanation["vector_store_consistency"] is None
    assert "determinism_fingerprint" in explanation
