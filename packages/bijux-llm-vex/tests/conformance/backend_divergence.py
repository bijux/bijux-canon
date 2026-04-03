# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.execution_intent import ExecutionIntent

import pytest

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import BackendDivergenceError
from bijux_vex.core.identity.ids import fingerprint
from bijux_vex.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    ExecutionRequest,
    Vector,
)
from tests.conformance.suite import default_backends, parametrize_backends


def _seed(backend):
    doc = Document(document_id="doc", text="hello")
    chunk = Chunk(
        chunk_id="chunk", document_id=doc.document_id, text="hello", ordinal=0
    )
    vec = Vector(vector_id="vec", chunk_id=chunk.chunk_id, values=(0.0,), dimension=1)
    art = ExecutionArtifact(
        artifact_id="art",
        corpus_fingerprint="corp",
        vector_fingerprint="vec",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.DETERMINISTIC,
        build_params=(),
    )
    with backend.tx_factory() as tx:
        backend.stores.vectors.put_document(tx, doc)
        backend.stores.vectors.put_chunk(tx, chunk)
        backend.stores.vectors.put_vector(tx, vec)
        backend.stores.ledger.put_artifact(tx, art)
    return doc, chunk, vec, art


def test_memory_sqlite_divergence_detection():
    backends = list(default_backends())
    mem = next(b.factory() for b in backends if b.name == "memory")
    sql = next(b.factory() for b in backends if b.name == "sqlite")
    doc, chunk, vec, art = _seed(mem)
    _seed(sql)
    query = ExecutionRequest(
        request_id="q",
        text=None,
        vector=(0.0,),
        top_k=1,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
    )
    mem_res = tuple(mem.stores.vectors.query(art.artifact_id, query))
    sql_res = tuple(sql.stores.vectors.query(art.artifact_id, query))
    if fingerprint(mem_res) != fingerprint(sql_res):
        raise BackendDivergenceError(message="memory vs sqlite divergence detected")
