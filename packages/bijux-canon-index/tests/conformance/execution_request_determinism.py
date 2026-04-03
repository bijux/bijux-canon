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
from tests.conformance.suite import default_backends, parametrize_backends


@parametrize_backends(default_backends())
def test_tie_break_order_is_stable(backend_case):
    fixture = backend_case.factory()
    doc = Document(document_id="doc-q", text="text")
    chunk_a = Chunk(
        chunk_id="chunk-a", document_id=doc.document_id, text="a", ordinal=0
    )
    chunk_b = Chunk(
        chunk_id="chunk-b", document_id=doc.document_id, text="b", ordinal=1
    )
    vec_a = Vector(
        vector_id="vec-a", chunk_id=chunk_a.chunk_id, values=(1.0, 0.0), dimension=2
    )
    vec_b = Vector(
        vector_id="vec-b", chunk_id=chunk_b.chunk_id, values=(0.0, 1.0), dimension=2
    )
    query = ExecutionRequest(
        request_id="q1",
        text=None,
        vector=(0.0, 0.0),
        top_k=2,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
    )
    artifact = ExecutionArtifact(
        artifact_id="artifact-q",
        corpus_fingerprint="corp-q",
        vector_fingerprint="vecset-q",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.DETERMINISTIC,
    )

    with fixture.tx_factory() as tx:
        fixture.authz.check(
            tx, action="put_document", resource="document", actor="tester"
        )
        fixture.stores.vectors.put_document(tx, doc)
        fixture.authz.check(tx, action="put_chunk", resource="chunk", actor="tester")
        fixture.stores.vectors.put_chunk(tx, chunk_a)
        fixture.stores.vectors.put_chunk(tx, chunk_b)
        fixture.authz.check(tx, action="put_vector", resource="vector", actor="tester")
        fixture.stores.vectors.put_vector(tx, vec_a)
        fixture.stores.vectors.put_vector(tx, vec_b)
        fixture.authz.check(
            tx, action="put_artifact", resource="artifact", actor="tester"
        )
        fixture.stores.ledger.put_artifact(tx, artifact)

    results = list(fixture.stores.vectors.query(artifact.artifact_id, query))
    assert [r.vector_id for r in results] == ["vec-a", "vec-b"]
    assert results[0].score == results[1].score
    assert results[0].rank == 1
    assert results[1].rank == 2


@parametrize_backends(default_backends())
def test_insertion_order_does_not_affect_ranking(backend_case):
    fixture = backend_case.factory()
    doc = Document(document_id="doc-q2", text="text")
    chunk_a = Chunk(
        chunk_id="chunk-a2", document_id=doc.document_id, text="a", ordinal=0
    )
    chunk_b = Chunk(
        chunk_id="chunk-b2", document_id=doc.document_id, text="b", ordinal=1
    )
    vectors = [
        Vector(
            vector_id="vec-a2",
            chunk_id=chunk_a.chunk_id,
            values=(1.0, 0.0),
            dimension=2,
        ),
        Vector(
            vector_id="vec-b2",
            chunk_id=chunk_b.chunk_id,
            values=(0.0, 1.0),
            dimension=2,
        ),
    ]
    query = ExecutionRequest(
        request_id="q2",
        text=None,
        vector=(0.0, 0.0),
        top_k=2,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
    )
    artifact = ExecutionArtifact(
        artifact_id="artifact-q2",
        corpus_fingerprint="corp-q2",
        vector_fingerprint="vecset-q2",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.DETERMINISTIC,
    )

    for order in (vectors, list(reversed(vectors))):
        state = backend_case.factory()
        with state.tx_factory() as tx:
            state.authz.check(
                tx, action="put_document", resource="document", actor="tester"
            )
            state.stores.vectors.put_document(tx, doc)
            state.authz.check(tx, action="put_chunk", resource="chunk", actor="tester")
            state.stores.vectors.put_chunk(tx, chunk_a)
            state.stores.vectors.put_chunk(tx, chunk_b)
            state.authz.check(
                tx, action="put_vector", resource="vector", actor="tester"
            )
            for vec in order:
                state.stores.vectors.put_vector(tx, vec)
            state.authz.check(
                tx, action="put_artifact", resource="artifact", actor="tester"
            )
            state.stores.ledger.put_artifact(tx, artifact)
        results = list(state.stores.vectors.query(artifact.artifact_id, query))
        assert [r.vector_id for r in results] == ["vec-a2", "vec-b2"]
