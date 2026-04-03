# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.execution_intent import ExecutionIntent

import random
import time

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    ExecutionRequest,
    Vector,
)
from bijux_vex.infra.adapters.memory.backend import memory_backend


def test_medium_scale_query_is_deterministic():
    rng = random.Random(1234)
    backend = memory_backend()
    dim = 4
    vectors = []
    with backend.tx_factory() as tx:
        for i in range(5000):
            values = tuple(rng.random() for _ in range(dim))
            doc = Document(document_id=f"d{i}", text=f"doc-{i}")
            chunk = Chunk(
                chunk_id=f"c{i}", document_id=doc.document_id, text=doc.text, ordinal=0
            )
            vec = Vector(
                vector_id=f"v{i}",
                chunk_id=chunk.chunk_id,
                values=values,
                dimension=dim,
            )
            backend.stores.vectors.put_document(tx, doc)
            backend.stores.vectors.put_chunk(tx, chunk)
            backend.stores.vectors.put_vector(tx, vec)
            vectors.append(vec)
        backend.stores.ledger.put_artifact(
            tx,
            ExecutionArtifact(
                artifact_id="art-big",
                corpus_fingerprint="big-corp",
                vector_fingerprint="big-vec",
                metric="l2",
                scoring_version="v1",
                execution_contract=ExecutionContract.DETERMINISTIC,
            ),
        )

    query_vec = vectors[0].values
    query = ExecutionRequest(
        request_id="q-big",
        text=None,
        vector=query_vec,
        top_k=5,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
    )

    start = time.perf_counter()
    first = list(backend.stores.vectors.query("art-big", query))
    second = list(backend.stores.vectors.query("art-big", query))
    duration = time.perf_counter() - start

    assert [r.vector_id for r in first] == [r.vector_id for r in second]
    assert duration < 3.0  # modest scale should stay snappy
