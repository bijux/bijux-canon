# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.runtime.vector_execution import RandomnessProfile
from bijux_vex.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    ExecutionBudget,
    ExecutionRequest,
    Vector,
)
from bijux_vex.domain.execution_requests.execute import (
    execute_request,
    start_execution_session,
)
from bijux_vex.infra.adapters.ann_reference import ReferenceAnnRunner
from bijux_vex.infra.adapters.memory.backend import memory_backend


def test_nd_result_emits_quality_or_reason():
    backend = memory_backend()
    with backend.tx_factory() as tx:
        doc = Document(document_id="d", text="hello")
        chunk = Chunk(chunk_id="c", document_id="d", text="hello", ordinal=0)
        vec = Vector(vector_id="v", chunk_id="c", values=(0.0,), dimension=1)
        artifact = ExecutionArtifact(
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
        backend.stores.ledger.put_artifact(tx, artifact)

    ann = ReferenceAnnRunner(backend.stores.vectors)
    ann.build_index("art", backend.stores.vectors.list_vectors(), "l2", None)
    request = ExecutionRequest(
        request_id="req",
        text=None,
        vector=(0.0,),
        top_k=1,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
        execution_mode=ExecutionMode.BOUNDED,
        execution_budget=ExecutionBudget(),
    )
    session = start_execution_session(
        artifact,
        request,
        backend.stores,
        randomness=RandomnessProfile(
            seed=1, sources=("seed",), bounded=True, non_replayable=False
        ),
        ann_runner=ann,
    )
    execution_result, _ = execute_request(session, backend.stores, ann_runner=ann)
    assert execution_result.nd_result is not None
    assert (
        execution_result.nd_result.quality is not None
        or execution_result.nd_result.quality_reason is not None
    )
