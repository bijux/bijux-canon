# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi <bijan@bijux.io>
from __future__ import annotations

from collections.abc import Iterable
from typing import Any, cast

from bijux_canon_index.application.engine import VectorExecutionEngine
from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.errors import BackendUnavailableError
from bijux_canon_index.core.execution_intent import ExecutionIntent
from bijux_canon_index.core.execution_mode import ExecutionMode
from bijux_canon_index.core.execution_result import ApproximationReport
from bijux_canon_index.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    Result,
    Vector,
)
from bijux_canon_index.infra.adapters.ann_base import AnnExecutionRequestRunner
from bijux_canon_index.infra.adapters.memory.backend import memory_backend
from bijux_canon_index.interfaces.errors import refusal_payload
from bijux_canon_index.interfaces.schemas.models import (
    ExecutionBudgetPayload,
    ExecutionRequestPayload,
    RandomnessProfilePayload,
)
import pytest


class FailingAnn(AnnExecutionRequestRunner):
    def __init__(self, stores: Any) -> None:
        self.stores = stores

    @property
    def randomness_sources(self) -> tuple[str, ...]:
        return ("ann",)

    @property
    def reproducibility_bounds(self) -> str:
        return "unreliable"

    def approximate_request(
        self, artifact: ExecutionArtifact, request: object
    ) -> Iterable[Result]:
        del artifact, request
        raise BackendUnavailableError(message="Injected failure for circuit breaker")

    def approximation_report(
        self, artifact: ExecutionArtifact, request: object, results: Iterable[object]
    ) -> ApproximationReport:
        del artifact, request, results
        raise BackendUnavailableError(message="Injected failure for circuit breaker")


def test_nd_circuit_breaker_refuses_after_failures() -> None:
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
    backend = cast(Any, backend)._replace(ann=ann)
    engine = VectorExecutionEngine(backend=backend)
    engine.backend = backend
    engine._nd_guard.max_failures = 1
    engine._nd_guard.cooldown_seconds = 60

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
