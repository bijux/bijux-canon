# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
from __future__ import annotations
import pytest

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.types import Chunk, Document, ExecutionArtifact, Vector
from tests.conformance.suite import default_backends, parametrize_backends


@parametrize_backends(default_backends())
def test_document_and_chunk_round_trip(backend_case):
    fixture = backend_case.factory()
    doc = Document(document_id="doc-1", text="hello world", source="unit", version="v1")
    chunk = Chunk(
        chunk_id="chunk-1", document_id=doc.document_id, text=doc.text, ordinal=0
    )

    with fixture.tx_factory() as tx:
        fixture.authz.check(
            tx, action="put_document", resource="document", actor="tester"
        )
        fixture.stores.vectors.put_document(tx, doc)
        fixture.authz.check(tx, action="put_chunk", resource="chunk", actor="tester")
        fixture.stores.vectors.put_chunk(tx, chunk)

    assert fixture.stores.vectors.get_document(doc.document_id) == doc
    chunks = list(fixture.stores.vectors.list_chunks(document_id=doc.document_id))
    assert chunks == [chunk]


@parametrize_backends(default_backends())
def test_vector_and_artifact_round_trip(backend_case):
    fixture = backend_case.factory()
    vector = Vector(
        vector_id="vec-1",
        chunk_id="chunk-1",
        values=(0.1, 0.2),
        dimension=2,
        model="m1",
    )
    artifact = ExecutionArtifact(
        artifact_id="art-1",
        corpus_fingerprint="corp-fp",
        vector_fingerprint="vec-fp",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.DETERMINISTIC,
    )

    with fixture.tx_factory() as tx:
        fixture.authz.check(tx, action="put_vector", resource="vector", actor="tester")
        fixture.stores.vectors.put_vector(tx, vector)
        fixture.authz.check(
            tx, action="put_artifact", resource="artifact", actor="tester"
        )
        fixture.stores.ledger.put_artifact(tx, artifact)

    assert fixture.stores.vectors.get_vector(vector.vector_id) == vector
    assert list(fixture.stores.vectors.list_vectors()) == [vector]
    assert fixture.stores.ledger.get_artifact(artifact.artifact_id) == artifact
    assert list(fixture.stores.ledger.list_artifacts()) == [artifact]
