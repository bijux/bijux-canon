# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.execution_intent import ExecutionIntent

import pytest

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.errors import InvariantError, ValidationError
from bijux_vex.core.execution_result import ApproximationReport
from bijux_vex.core.runtime.vector_execution import RandomnessProfile
from bijux_vex.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    ExecutionRequest,
    ExecutionBudget,
    Result,
    Vector,
)
from bijux_vex.domain.execution_requests.execute import (
    execute_request,
    start_execution_session,
)
from bijux_vex.domain.provenance.lineage import explain_result
from bijux_vex.domain.provenance.replay import replay
from bijux_vex.infra.adapters.ann_base import AnnExecutionRequestRunner
from bijux_vex.infra.adapters.memory.backend import memory_backend


class FlappingAnn(AnnExecutionRequestRunner):
    def __init__(self, stores):
        self.stores = stores
        self.flip = False

    @property
    def randomness_sources(self) -> tuple[str, ...]:
        return ("ordering_flip",)

    @property
    def reproducibility_bounds(self) -> str:
        return "top-k ordering may flip across runs"

    def approximate_request(self, artifact: ExecutionArtifact, query: ExecutionRequest):
        vectors = list(self.stores.vectors.list_vectors())
        results: list[Result] = []
        for vec in vectors:
            chunk = self.stores.vectors.get_chunk(vec.chunk_id)
            doc_id = chunk.document_id if chunk else ""
            results.append(
                Result(
                    request_id=query.request_id,
                    document_id=doc_id,
                    chunk_id=vec.chunk_id,
                    vector_id=vec.vector_id,
                    artifact_id=artifact.artifact_id,
                    score=float(len(results)),
                    rank=0,
                )
            )
        results.sort(key=lambda r: r.vector_id)
        if self.flip:
            results.reverse()
        self.flip = not self.flip
        final = results[: query.top_k]
        return tuple(
            Result(
                request_id=r.request_id,
                document_id=r.document_id,
                chunk_id=r.chunk_id,
                vector_id=r.vector_id,
                artifact_id=r.artifact_id,
                score=float(idx),
                rank=idx,
            )
            for idx, r in enumerate(final, start=1)
        )

    def approximation_report(
        self, artifact: ExecutionArtifact, request: ExecutionRequest, results
    ):
        return ApproximationReport(
            recall_at_k=1.0,
            rank_displacement=0.0,
            distance_error=0.0,
            algorithm="flapping-ann",
            backend="memory",
            randomness_sources=self.randomness_sources,
            deterministic_fallback_used=False,
            algorithm_version="test",
            truncation_ratio=1.0,
        )


def _seed_backend(
    contract: ExecutionContract, ann: AnnExecutionRequestRunner | None = None
):
    backend = memory_backend()
    with backend.tx_factory() as tx:
        doc = Document(document_id="doc", text="hi")
        chunk = Chunk(
            chunk_id="chunk", document_id=doc.document_id, text=doc.text, ordinal=0
        )
        backend.stores.vectors.put_document(tx, doc)
        backend.stores.vectors.put_chunk(tx, chunk)
        backend.stores.vectors.put_vector(
            tx,
            Vector(
                vector_id="v1",
                chunk_id=chunk.chunk_id,
                values=(0.0, 0.0),
                dimension=2,
            ),
        )
        backend.stores.vectors.put_vector(
            tx,
            Vector(
                vector_id="v2",
                chunk_id=chunk.chunk_id,
                values=(1.0, 1.0),
                dimension=2,
            ),
        )
        backend.stores.ledger.put_artifact(
            tx,
            ExecutionArtifact(
                artifact_id="art",
                corpus_fingerprint="corp",
                vector_fingerprint="vec",
                metric="l2",
                scoring_version="v1",
                execution_contract=contract,
                execution_id=(
                    "art-nd-execution"
                    if contract is ExecutionContract.NON_DETERMINISTIC
                    else ""
                ),
            ),
        )
    if ann:
        backend = backend._replace(ann=ann)  # type: ignore[attr-defined]
    return backend


def _request(contract: ExecutionContract) -> ExecutionRequest:
    budget = None
    mode = ExecutionMode.STRICT
    if contract is ExecutionContract.NON_DETERMINISTIC:
        budget = ExecutionBudget(max_latency_ms=10, max_memory_mb=10, max_error=0.1)
        mode = ExecutionMode.BOUNDED
    return ExecutionRequest(
        request_id="req",
        text=None,
        vector=(0.0, 0.0),
        top_k=1,
        execution_contract=contract,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
        execution_mode=mode,
        execution_budget=budget,
    )


def test_contract_drives_distinct_plans():
    backend_det = _seed_backend(ExecutionContract.DETERMINISTIC)
    artifact_det = backend_det.stores.ledger.get_artifact("art")
    backend_nd = _seed_backend(
        ExecutionContract.NON_DETERMINISTIC, ann=FlappingAnn(None)
    )
    backend_nd.ann.stores = backend_nd.stores  # type: ignore[attr-defined]
    artifact_nd = backend_nd.stores.ledger.get_artifact("art")
    req_det = _request(ExecutionContract.DETERMINISTIC)
    req_nd = _request(ExecutionContract.NON_DETERMINISTIC)
    session_det = start_execution_session(
        artifact_det, req_det, backend_det.stores, ann_runner=None
    )
    session_nd = start_execution_session(
        artifact_nd, req_nd, backend_nd.stores, ann_runner=backend_nd.ann
    )
    exec_det, _ = execute_request(session_det, backend_det.stores)
    exec_nd, _ = execute_request(
        session_nd,
        backend_nd.stores,
        ann_runner=backend_nd.ann,
    )
    assert exec_det.plan.steps != exec_nd.plan.steps


def test_deterministic_replay_is_identical():
    backend = _seed_backend(ExecutionContract.DETERMINISTIC)
    artifact = backend.stores.ledger.get_artifact("art")
    request = _request(ExecutionContract.DETERMINISTIC)

    session = start_execution_session(artifact, request, backend.stores)
    exec_one, first_iter = execute_request(session, backend.stores)
    first = tuple(first_iter)
    exec_two, second_iter = execute_request(session, backend.stores)
    second = tuple(second_iter)
    assert first == second
    assert exec_one.execution_id == exec_two.execution_id

    with backend.tx_factory() as tx:
        backend.stores.ledger.put_execution_result(tx, exec_two)
    outcome = replay(request, artifact, backend.stores, baseline_fingerprint=None)
    assert outcome.matches is True
    assert outcome.nondeterministic_sources == ()
    assert outcome.details == {}


def test_non_deterministic_replay_declares_divergence():
    ann = FlappingAnn(None)
    backend = _seed_backend(ExecutionContract.NON_DETERMINISTIC, ann=ann)
    ann.stores = backend.stores  # late bind after backend creation
    artifact = backend.stores.ledger.get_artifact("art")
    request = _request(ExecutionContract.NON_DETERMINISTIC)

    session_one = start_execution_session(
        artifact, request, backend.stores, ann_runner=ann
    )
    exec_one, first_iter = execute_request(session_one, backend.stores, ann_runner=ann)
    first = tuple(first_iter)
    session_two = start_execution_session(
        artifact, request, backend.stores, ann_runner=ann
    )
    exec_two, second_iter = execute_request(session_two, backend.stores, ann_runner=ann)
    second = tuple(second_iter)
    assert first != second
    assert exec_one.execution_id != exec_two.execution_id

    with backend.tx_factory() as tx:
        backend.stores.ledger.put_execution_result(tx, exec_two)
    outcome = replay(
        request,
        artifact,
        backend.stores,
        ann_runner=ann,
        randomness=RandomnessProfile(seed=1, sources=("ann",), non_replayable=False),
        baseline_fingerprint=None,
    )
    assert outcome.execution_contract is ExecutionContract.NON_DETERMINISTIC
    assert outcome.nondeterministic_sources == ("ordering_flip",)
    assert "execution_contract" in outcome.details
    assert outcome.matches is False

    provenance = explain_result(first[0], backend.stores)
    assert provenance["nondeterministic_sources"] == ("approximate_execution",)
    assert provenance["lossy_dimensions"] == ("ranking",)


def test_cross_contract_request_rejected():
    ann = FlappingAnn(None)
    backend = _seed_backend(ExecutionContract.NON_DETERMINISTIC, ann=ann)
    ann.stores = backend.stores  # late bind after backend creation
    artifact = backend.stores.ledger.get_artifact("art")
    deterministic_request = _request(ExecutionContract.DETERMINISTIC)

    with pytest.raises((InvariantError, ValidationError)):
        execute_request(
            start_execution_session(
                artifact, deterministic_request, backend.stores, ann_runner=ann
            ),
            backend.stores,
            ann_runner=ann,
        )
