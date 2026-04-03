# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.execution_intent import ExecutionIntent

import pytest

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.execution_result import ApproximationReport
from bijux_vex.core.errors import BudgetExceededError
from bijux_vex.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    ExecutionBudget,
    ExecutionRequest,
    Result,
    Vector,
)
from bijux_vex.domain.execution_requests.execute import (
    execute_request,
    start_execution_session,
)
from bijux_vex.domain.provenance.replay import replay
from bijux_vex.infra.adapters.ann_base import AnnExecutionRequestRunner
from bijux_vex.infra.adapters.memory.backend import memory_backend


class FallbackAnn(AnnExecutionRequestRunner):
    def __init__(self, stores):
        self.stores = stores
        self.fallback_used = False

    @property
    def randomness_sources(self) -> tuple[str, ...]:
        return ("ann_random",)

    @property
    def reproducibility_bounds(self) -> str:
        return "approximate"

    def approximate_request(self, artifact, request):
        self.fallback_used = True
        return self.deterministic_fallback(artifact.artifact_id, request)

    def deterministic_fallback(self, artifact_id: str, request: ExecutionRequest):
        self.fallback_used = True
        return self.stores.vectors.query(artifact_id, request)

    def approximation_report(self, artifact, request, results):
        return ApproximationReport(
            recall_at_k=1.0,
            rank_displacement=0.0,
            distance_error=0.0,
            algorithm="fallback-ann",
            backend="memory",
            randomness_sources=self.randomness_sources,
            deterministic_fallback_used=self.fallback_used,
            algorithm_version="test",
            truncation_ratio=1.0,
        )


def _seed_backend(contract: ExecutionContract, count: int = 3):
    backend = memory_backend()
    with backend.tx_factory() as tx:
        doc = Document(document_id="doc", text="text")
        backend.stores.vectors.put_document(tx, doc)
        for i in range(count):
            chunk = Chunk(
                chunk_id=f"chunk-{i}",
                document_id=doc.document_id,
                text="text",
                ordinal=i,
            )
            backend.stores.vectors.put_chunk(tx, chunk)
            backend.stores.vectors.put_vector(
                tx,
                Vector(
                    vector_id=f"v{i}",
                    chunk_id=chunk.chunk_id,
                    values=(float(i), float(i)),
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
            ),
        )
    return backend


def _request(contract: ExecutionContract, budget: ExecutionBudget | None = None):
    return ExecutionRequest(
        request_id="req",
        text=None,
        vector=(0.0, 0.0),
        top_k=1,
        execution_contract=contract,
        execution_intent=(
            ExecutionIntent.EXACT_VALIDATION
            if contract is ExecutionContract.DETERMINISTIC
            else ExecutionIntent.EXPLORATORY_SEARCH
        ),
        execution_mode=(
            ExecutionMode.STRICT
            if contract is ExecutionContract.DETERMINISTIC
            else ExecutionMode.BOUNDED
        ),
        execution_budget=budget,
    )


def test_deterministic_replay_hash_matches():
    backend = _seed_backend(ExecutionContract.DETERMINISTIC)
    artifact = backend.stores.ledger.get_artifact("art")
    req = _request(ExecutionContract.DETERMINISTIC)
    session = start_execution_session(artifact, req, backend.stores)
    exec_one, results_one = execute_request(session, backend.stores)
    exec_two, results_two = execute_request(session, backend.stores)
    assert tuple(results_one) == tuple(results_two)
    with backend.tx_factory() as tx:
        backend.stores.ledger.put_execution_result(tx, exec_one)
    outcome = replay(req, artifact, backend.stores)
    assert outcome.matches is True


def test_nd_emits_determinism_report():
    backend = _seed_backend(ExecutionContract.NON_DETERMINISTIC)
    ann = FallbackAnn(backend.stores)
    backend = backend._replace(ann=ann)  # type: ignore[attr-defined]
    artifact = backend.stores.ledger.get_artifact("art")
    req = _request(
        ExecutionContract.NON_DETERMINISTIC,
        budget=ExecutionBudget(max_latency_ms=5, max_memory_mb=5, max_error=1.0),
    )
    session = start_execution_session(artifact, req, backend.stores, ann_runner=ann)
    execution_result, _ = execute_request(session, backend.stores, ann_runner=ann)
    assert execution_result.determinism_report is not None
    assert execution_result.determinism_report.randomness_sources
    assert ann.fallback_used


def test_budget_exhaustion_mid_plan():
    backend = _seed_backend(ExecutionContract.NON_DETERMINISTIC, count=5)
    ann = FallbackAnn(backend.stores)
    backend = backend._replace(ann=ann)  # type: ignore[attr-defined]
    artifact = backend.stores.ledger.get_artifact("art")
    req = _request(
        ExecutionContract.NON_DETERMINISTIC,
        budget=ExecutionBudget(
            max_latency_ms=1, max_memory_mb=1, max_error=0.1, max_vectors=0
        ),
    )
    session = start_execution_session(artifact, req, backend.stores, ann_runner=ann)
    execution_result, _ = execute_request(session, backend.stores, ann_runner=ann)
    assert execution_result.status.name == "PARTIAL"
    assert execution_result.failure_reason is not None
    assert execution_result.failure_reason.startswith("budget_exhausted")


def test_ann_fallback_forced():
    backend = _seed_backend(ExecutionContract.NON_DETERMINISTIC)
    ann = FallbackAnn(backend.stores)
    backend = backend._replace(ann=ann)  # type: ignore[attr-defined]
    artifact = backend.stores.ledger.get_artifact("art")
    req = _request(
        ExecutionContract.NON_DETERMINISTIC,
        budget=ExecutionBudget(max_latency_ms=10, max_memory_mb=10, max_error=1.0),
    )
    session = start_execution_session(artifact, req, backend.stores, ann_runner=ann)
    execution_result, results = execute_request(session, backend.stores, ann_runner=ann)
    assert ann.fallback_used
    assert isinstance(execution_result.results, tuple)
    assert all(isinstance(r, Result) for r in results)
