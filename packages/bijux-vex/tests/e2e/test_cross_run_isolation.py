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
from bijux_vex.infra.adapters.memory.backend import memory_backend


def _run_pipeline(prefix: str):
    backend = memory_backend()
    doc = Document(document_id=f"{prefix}-doc", text="hello")
    chunk = Chunk(
        chunk_id=f"{prefix}-chunk",
        document_id=doc.document_id,
        text=doc.text,
        ordinal=0,
    )
    vec = Vector(
        vector_id=f"{prefix}-vec",
        chunk_id=chunk.chunk_id,
        values=(0.0, 0.0),
        dimension=2,
    )
    artifact = ExecutionArtifact(
        artifact_id=f"{prefix}-art",
        corpus_fingerprint=f"{prefix}-corp",
        vector_fingerprint=f"{prefix}-vecfp",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.DETERMINISTIC,
    )
    with backend.tx_factory() as tx:
        backend.stores.vectors.put_document(tx, doc)
        backend.stores.vectors.put_chunk(tx, chunk)
        backend.stores.vectors.put_vector(tx, vec)
        backend.stores.ledger.put_artifact(tx, artifact)
    results = list(
        backend.stores.vectors.query(
            artifact.artifact_id,
            ExecutionRequest(
                request_id=f"q-{prefix}",
                text=None,
                vector=(0.0, 0.0),
                top_k=1,
                execution_contract=ExecutionContract.DETERMINISTIC,
                execution_intent=ExecutionIntent.EXACT_VALIDATION,
            ),
        )
    )
    return backend, results, artifact


def test_cross_run_state_is_isolated():
    backend_a, results_a, art_a = _run_pipeline("a")
    backend_b, results_b, art_b = _run_pipeline("b")

    assert backend_a.stores.vectors.get_document("b-doc") is None
    assert backend_b.stores.vectors.get_document("a-doc") is None

    assert backend_a.stores.ledger.get_artifact(art_b.artifact_id) is None
    assert backend_b.stores.ledger.get_artifact(art_a.artifact_id) is None

    assert (
        backend_a.stores.vectors._state.audit_log
        is not backend_b.stores.vectors._state.audit_log
    )  # type: ignore[attr-defined]
    assert results_a[0].vector_id != results_b[0].vector_id
