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
from bijux_vex.infra.adapters.sqlite.backend import sqlite_backend


def _seed_backend(
    backend, prefix: str = ""
) -> tuple[ExecutionArtifact, ExecutionRequest]:
    doc = Document(document_id=f"{prefix}doc", text="hello")
    chunk = Chunk(
        chunk_id=f"{prefix}chunk", document_id=doc.document_id, text=doc.text, ordinal=0
    )
    vec = Vector(
        vector_id=f"{prefix}vec",
        chunk_id=chunk.chunk_id,
        values=(0.0, 0.0),
        dimension=2,
    )
    artifact = ExecutionArtifact(
        artifact_id=f"{prefix}art",
        corpus_fingerprint=f"{prefix}corp",
        vector_fingerprint=f"{prefix}vecfp",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.DETERMINISTIC,
    )
    with backend.tx_factory() as tx:
        backend.stores.vectors.put_document(tx, doc)
        backend.stores.vectors.put_chunk(tx, chunk)
        backend.stores.vectors.put_vector(tx, vec)
        backend.stores.ledger.put_artifact(tx, artifact)
    query = ExecutionRequest(
        request_id=f"{prefix}q",
        text=None,
        vector=(0.0, 0.0),
        top_k=1,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
    )
    return artifact, query


def test_replay_matches_across_backends(tmp_path):
    mem = memory_backend()
    mem_art, query = _seed_backend(mem, "m-")
    from bijux_vex.domain.execution_requests.execute import (
        execute_request,
        start_execution_session,
    )

    from bijux_vex.domain.provenance.replay import _results_fingerprint

    mem_session = start_execution_session(mem_art, query, mem.stores)
    mem_result, _ = execute_request(mem_session, mem.stores)
    with mem.tx_factory() as tx:
        mem.stores.ledger.put_execution_result(tx, mem_result)
    baseline_fp = _results_fingerprint(mem_result.results)
    baseline = replay(query, mem_art, mem.stores, baseline_fingerprint=baseline_fp)

    sqlite = sqlite_backend(tmp_path / "cross.sqlite")
    sql_art, query_sql = _seed_backend(sqlite, "m-")
    sql_session = start_execution_session(sql_art, query_sql, sqlite.stores)
    sql_result, _ = execute_request(sql_session, sqlite.stores)
    with sqlite.tx_factory() as tx:
        sqlite.stores.ledger.put_execution_result(tx, sql_result)
    outcome = replay(query_sql, sql_art, sqlite.stores, baseline.original_fingerprint)

    assert outcome.matches is True
    assert outcome.original_fingerprint == baseline.original_fingerprint
