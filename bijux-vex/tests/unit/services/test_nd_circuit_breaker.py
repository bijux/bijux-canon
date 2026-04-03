# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import pytest

from bijux_vex.boundaries.exception_bridge import refusal_payload
from bijux_vex.boundaries.pydantic_edges.models import (
    ExecutionBudgetPayload,
    ExecutionRequestPayload,
    RandomnessProfilePayload,
)
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import BackendUnavailableError
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.types import Chunk, Document, ExecutionArtifact, Vector
from bijux_vex.infra.adapters.ann_base import AnnExecutionRequestRunner
from bijux_vex.infra.adapters.memory.backend import memory_backend
from bijux_vex.services.execution_engine import VectorExecutionEngine


class FailingAnn(AnnExecutionRequestRunner):
    def __init__(self, stores):
        self.stores = stores

    @property
    def randomness_sources(self) -> tuple[str, ...]:
        return ("ann",)

    @property
    def reproducibility_bounds(self) -> str:
        return "unreliable"

    def approximate_request(self, artifact, request):  # type: ignore[override]
        raise BackendUnavailableError(message="Injected failure for circuit breaker")

    def approximation_report(self, artifact, request, results):  # type: ignore[override]
        raise BackendUnavailableError(message="Injected failure for circuit breaker")


def test_nd_circuit_breaker_refuses_after_failures():
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
    ann = FailingAnn(backend.stores)
    backend = backend._replace(ann=ann)  # type: ignore[attr-defined]
    engine = VectorExecutionEngine(backend=backend)
    engine.backend = backend  # type: ignore[assignment]
    engine._nd_circuit_max_failures = 1  # type: ignore[attr-defined]
    engine._nd_circuit_cooldown_s = 60  # type: ignore[attr-defined]

    req = ExecutionRequestPayload(
        request_text=None,
        vector=(0.0,),
        top_k=1,
        artifact_id="art",
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
        execution_mode=ExecutionMode.BOUNDED,
        execution_budget=ExecutionBudgetPayload(
            max_latency_ms=10, max_memory_mb=10, max_error=1.0
        ),
        nd_build_on_demand=True,
        randomness_profile=RandomnessProfilePayload(
            seed=1, sources=("seed",), bounded=True, non_replayable=False
        ),
    )

    with pytest.raises(BackendUnavailableError):
        engine.execute(req)

    with pytest.raises(BackendUnavailableError) as excinfo:
        engine.execute(req)
    payload = refusal_payload(excinfo.value)
    assert payload["reason"] == "backend_unavailable"
