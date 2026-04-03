# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import pytest
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    ExecutionBudget,
    ExecutionRequest,
    NDSettings,
    Vector,
)
from bijux_vex.domain.execution_requests.execute import (
    execute_request,
    start_execution_session,
)
from bijux_vex.infra.adapters.ann_hnsw import HnswAnnRunner
from bijux_vex.infra.adapters.memory.backend import memory_backend


pytest.importorskip("hnswlib")


def _setup_backend():
    backend = memory_backend()
    with backend.tx_factory() as tx:
        doc = Document(document_id="d", text="hello")
        chunk = Chunk(
            chunk_id="c", document_id=doc.document_id, text="hello", ordinal=0
        )
        vec = Vector(vector_id="v", chunk_id=chunk.chunk_id, values=(0.0,), dimension=1)
        art = ExecutionArtifact(
            artifact_id="art",
            corpus_fingerprint="corp",
            vector_fingerprint="vec",
            metric="l2",
            scoring_version="v1",
            execution_contract=ExecutionContract.NON_DETERMINISTIC,
        )
        backend.stores.vectors.put_document(tx, doc)
        backend.stores.vectors.put_chunk(tx, chunk)
        backend.stores.vectors.put_vector(tx, vec)
        backend.stores.ledger.put_artifact(tx, art)
    return backend


@pytest.mark.parametrize(
    "budget,nd_settings",
    [
        (ExecutionBudget(max_vectors=0, max_memory_mb=10, max_error=1.0), None),
        (
            ExecutionBudget(
                max_distance_computations=0, max_memory_mb=10, max_error=1.0
            ),
            None,
        ),
        (
            ExecutionBudget(max_latency_ms=10, max_memory_mb=10, max_error=1.0),
            NDSettings(max_candidates=0),
        ),
    ],
)
def test_nd_budget_enforced(budget, nd_settings):
    backend = _setup_backend()
    ann = HnswAnnRunner(backend.stores.vectors)
    ann.build_index(
        "art",
        backend.stores.vectors.list_vectors(),
        "l2",
        nd_settings,
    )
    request = ExecutionRequest(
        request_id="req",
        text=None,
        vector=(0.0,),
        top_k=1,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
        execution_mode=ExecutionMode.BOUNDED,
        execution_budget=budget,
        nd_settings=nd_settings,
    )
    session = start_execution_session(
        backend.stores.ledger.get_artifact("art"),
        request,
        backend.stores,
        ann_runner=ann,
    )
    execution_result, _ = execute_request(session, backend.stores, ann_runner=ann)
    assert execution_result.status.name == "PARTIAL"
    assert execution_result.failure_reason is not None
    assert execution_result.failure_reason.startswith("budget_exhausted")
