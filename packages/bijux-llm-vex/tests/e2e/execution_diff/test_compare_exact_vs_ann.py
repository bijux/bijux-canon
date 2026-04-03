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
    ExecutionBudget,
    Vector,
)
from bijux_vex.domain.execution_requests.compare import compare_executions
from bijux_vex.domain.execution_requests.execute import (
    execute_request,
    start_execution_session,
)
from bijux_vex.infra.adapters.ann_base import AnnExecutionRequestRunner
from bijux_vex.infra.adapters.memory.backend import memory_backend


class ReversingAnn(AnnExecutionRequestRunner):
    def __init__(self, stores):
        self.stores = stores

    @property
    def randomness_sources(self) -> tuple[str, ...]:
        return ("ordering_flip",)

    @property
    def reproducibility_bounds(self) -> str:
        return "ordering may reverse"

    def approximate_request(self, artifact, request):  # type: ignore[override]
        vectors = list(self.stores.vectors.list_vectors())
        vectors.reverse()
        results = []
        for idx, vec in enumerate(vectors[: request.top_k], start=1):
            chunk = self.stores.vectors.get_chunk(vec.chunk_id)
            doc_id = chunk.document_id if chunk else ""
            from bijux_vex.core.types import Result

            results.append(
                Result(
                    request_id=request.request_id,
                    document_id=doc_id,
                    chunk_id=vec.chunk_id,
                    vector_id=vec.vector_id,
                    artifact_id=artifact.artifact_id,
                    score=float(idx),
                    rank=idx,
                )
            )
        return tuple(results)

    def approximation_report(self, artifact, request, results):
        return ApproximationReport(
            recall_at_k=1.0,
            rank_displacement=0.0,
            distance_error=0.0,
            algorithm="reversing-ann",
            backend="memory",
            randomness_sources=self.randomness_sources,
            deterministic_fallback_used=False,
            algorithm_version="test",
            truncation_ratio=1.0,
        )


def test_compare_exact_and_ann_results():
    backend = memory_backend()
    ann = ReversingAnn(backend.stores)
    backend = backend._replace(ann=ann)  # type: ignore[attr-defined]
    with backend.tx_factory() as tx:
        doc = Document(document_id="d1", text="hello")
        chunk = Chunk(
            chunk_id="c1", document_id=doc.document_id, text=doc.text, ordinal=0
        )
        vec_a = Vector(
            vector_id="v-a", chunk_id=chunk.chunk_id, values=(0.0, 0.0), dimension=2
        )
        vec_b = Vector(
            vector_id="v-b", chunk_id=chunk.chunk_id, values=(1.0, 1.0), dimension=2
        )
        backend.stores.vectors.put_document(tx, doc)
        backend.stores.vectors.put_chunk(tx, chunk)
        backend.stores.vectors.put_vector(tx, vec_a)
        backend.stores.vectors.put_vector(tx, vec_b)
        backend.stores.ledger.put_artifact(
            tx,
            ExecutionArtifact(
                artifact_id="art-det",
                corpus_fingerprint="corp",
                vector_fingerprint="vec",
                metric="l2",
                scoring_version="v1",
                execution_contract=ExecutionContract.DETERMINISTIC,
            ),
        )
        backend.stores.ledger.put_artifact(
            tx,
            ExecutionArtifact(
                artifact_id="art-ann",
                corpus_fingerprint="corp",
                vector_fingerprint="vec",
                metric="l2",
                scoring_version="v1",
                execution_contract=ExecutionContract.NON_DETERMINISTIC,
            ),
        )

    req_exact = ExecutionRequest(
        request_id="req-exact",
        text=None,
        vector=(0.0, 0.0),
        top_k=2,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
    )
    req_ann = ExecutionRequest(
        request_id="req-ann",
        text=None,
        vector=(0.0, 0.0),
        top_k=2,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
        execution_mode=ExecutionMode.BOUNDED,
        execution_budget=ExecutionBudget(
            max_latency_ms=10, max_memory_mb=10, max_error=0.2
        ),
    )

    art_exact = backend.stores.ledger.get_artifact("art-det")
    art_ann = backend.stores.ledger.get_artifact("art-ann")

    session_exact = start_execution_session(
        art_exact, req_exact, backend.stores, ann_runner=None
    )
    session_ann = start_execution_session(
        art_ann, req_ann, backend.stores, ann_runner=ann
    )
    exec_exact, res_exact = execute_request(session_exact, backend.stores)
    exec_ann, res_ann = execute_request(session_ann, backend.stores, ann_runner=ann)

    diff = compare_executions(exec_exact, res_exact, exec_ann, res_ann)
    assert diff.overlap_ratio > 0
    assert diff.rank_instability >= 0
    assert diff.execution_a.execution_id != diff.execution_b.execution_id
