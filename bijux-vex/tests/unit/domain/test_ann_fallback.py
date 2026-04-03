# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.execution_intent import ExecutionIntent

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.execution_result import ApproximationReport
from bijux_vex.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    ExecutionRequest,
    Vector,
    ExecutionBudget,
)
from bijux_vex.domain.execution_requests.execute import (
    execute_request,
    start_execution_session,
)
from bijux_vex.infra.adapters.ann_base import AnnExecutionRequestRunner
from bijux_vex.infra.adapters.memory.backend import memory_backend


class FallbackAnn(AnnExecutionRequestRunner):
    def __init__(self, stores):
        self.stores = stores
        self.force_fallback = True

    @property
    def randomness_sources(self) -> tuple[str, ...]:
        return ("ann",)

    @property
    def reproducibility_bounds(self) -> str:
        return "fallback"

    def ensure_contract(self, artifact):  # type: ignore[override]
        super().ensure_contract(artifact)

    def approximate_request(self, artifact, request):  # type: ignore[override]
        # should be bypassed due to force_fallback
        return ()

    def approximation_report(self, artifact, request, results):
        return ApproximationReport(
            recall_at_k=1.0,
            rank_displacement=0.0,
            distance_error=0.0,
            algorithm="fallback",
            backend="memory",
            randomness_sources=self.randomness_sources,
            deterministic_fallback_used=True,
            algorithm_version="test",
            truncation_ratio=1.0,
        )

    def deterministic_fallback(self, artifact_id: str, request: ExecutionRequest):
        return self.stores.vectors.query(artifact_id, request)


def test_ann_fallback_matches_exact():
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
    ann = FallbackAnn(backend.stores)
    backend = backend._replace(ann=ann)  # type: ignore[attr-defined]
    request = ExecutionRequest(
        request_id="req",
        text=None,
        vector=(0.0,),
        top_k=1,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
        execution_mode=ExecutionMode.BOUNDED,
        execution_budget=ExecutionBudget(
            max_latency_ms=10, max_memory_mb=10, max_error=1.0
        ),
    )
    session = start_execution_session(
        backend.stores.ledger.get_artifact("art"),
        request,
        backend.stores,
        ann_runner=ann,
    )
    exec_res, res = execute_request(session, backend.stores, ann_runner=ann)
    assert exec_res.randomness_sources
    exact_results = tuple(backend.stores.vectors.query("art", request))
    assert tuple(res) == exact_results
