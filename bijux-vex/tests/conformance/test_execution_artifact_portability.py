# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.execution_intent import ExecutionIntent

from dataclasses import asdict

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    ExecutionRequest,
    Vector,
)
from bijux_vex.infra.adapters.memory.backend import memory_backend
from bijux_vex.infra.adapters.sqlite.backend import sqlite_backend


def _ingest(
    backend, doc: Document, chunk: Chunk, vec: Vector, artifact: ExecutionArtifact
):
    with backend.tx_factory() as tx:
        backend.stores.vectors.put_document(tx, doc)
        backend.stores.vectors.put_chunk(tx, chunk)
        backend.stores.vectors.put_vector(tx, vec)
        backend.stores.ledger.put_artifact(tx, artifact)


def test_artifact_round_trip_between_backends(tmp_path):
    doc = Document(document_id="d1", text="hello")
    chunk = Chunk(chunk_id="c1", document_id=doc.document_id, text=doc.text, ordinal=0)
    vec = Vector(
        vector_id="v1",
        chunk_id=chunk.chunk_id,
        values=(0.0, 0.0),
        dimension=2,
    )
    artifact = ExecutionArtifact(
        artifact_id="art-1",
        corpus_fingerprint="corp-fp",
        vector_fingerprint="vec-fp",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.DETERMINISTIC,
    )
    mem = memory_backend()
    _ingest(mem, doc, chunk, vec, artifact)
    query = ExecutionRequest(
        request_id="q1",
        text=None,
        vector=(0.0, 0.0),
        top_k=5,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
    )
    mem_results = list(mem.stores.vectors.query("art-1", query))

    portable_kwargs = {k: v for k, v in asdict(artifact).items() if k != "replayable"}
    portable = ExecutionArtifact(**portable_kwargs)
    sqlite = sqlite_backend(tmp_path / "db.sqlite")
    _ingest(sqlite, doc, chunk, vec, portable)
    sqlite_results = list(sqlite.stores.vectors.query("art-1", query))

    mem_pairs = [(r.vector_id, r.score) for r in mem_results]
    sqlite_pairs = [(r.vector_id, r.score) for r in sqlite_results]
    assert mem_pairs == sqlite_pairs
