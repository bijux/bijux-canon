# SPDX-License-Identifier: MIT
# SPDX-License-Identifier: MIT
from __future__ import annotations
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.execution_intent import ExecutionIntent

from bijux_vex.core.errors import BudgetExceededError
from bijux_vex.core.execution_result import ApproximationReport
from bijux_vex.core.runtime.vector_execution import RandomnessProfile
from bijux_vex.core.contracts.execution_contract import ExecutionContract
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
from bijux_vex.domain.provenance.replay import replay
from bijux_vex.infra.adapters.ann_base import AnnExecutionRequestRunner
from bijux_vex.infra.adapters.memory.backend import memory_backend


class DivergingAnn(AnnExecutionRequestRunner):
    def __init__(self, stores, force_fallback: bool = False):
        self.stores = stores
        self.force_fallback = force_fallback
        self.fallback_used = False

    @property
    def randomness_sources(self) -> tuple[str, ...]:
        return ("ann_random",)

    @property
    def reproducibility_bounds(self) -> str:
        return "approximate"

    def approximate_request(self, artifact, request):
        if not self.force_fallback:
            self.force_fallback = True
            return self._exhaust_then_stop()
        return self.deterministic_fallback(artifact.artifact_id, request)

    def _exhaust_then_stop(self):
        def _gen():
            raise BudgetExceededError(
                message="ann budget exhausted mid-flight",
                dimension="ann_probes",
                partial_results=(),
            )
            yield from ()

        return _gen()

    def deterministic_fallback(self, artifact_id: str, request: ExecutionRequest):
        self.fallback_used = True
        return self.stores.vectors.query(artifact_id, request)

    def approximation_report(self, artifact, request, results):
        return ApproximationReport(
            recall_at_k=0.0,
            rank_displacement=0.0,
            distance_error=0.0,
            algorithm="diverging-ann",
            backend="memory",
            randomness_sources=self.randomness_sources,
            deterministic_fallback_used=self.fallback_used,
            algorithm_version="test",
            truncation_ratio=0.0,
        )


def _seed():
    backend = memory_backend()
    with backend.tx_factory() as tx:
        doc = Document(document_id="doc", text="text")
        backend.stores.vectors.put_document(tx, doc)
        chunk = Chunk(
            chunk_id="chunk",
            document_id=doc.document_id,
            text="text",
            ordinal=0,
        )
        backend.stores.vectors.put_chunk(tx, chunk)
        backend.stores.vectors.put_vector(
            tx,
            Vector(
                vector_id="v0",
                chunk_id=chunk.chunk_id,
                values=(0.1, 0.2),
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
                execution_contract=ExecutionContract.NON_DETERMINISTIC,
            ),
        )
    return backend


def test_forcing_scenario_budget_fallback_replay_divergence():
    backend = _seed()
    ann = DivergingAnn(backend.stores)
    backend = backend._replace(ann=ann)  # type: ignore[attr-defined]
    artifact = backend.stores.ledger.get_artifact("art")
    req = ExecutionRequest(
        request_id="req",
        text=None,
        vector=(0.0, 0.0),
        top_k=1,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
        execution_mode=ExecutionMode.BOUNDED,
        execution_budget=ExecutionBudget(
            max_vectors=10, max_latency_ms=10, max_memory_mb=10, max_ann_probes=1
        ),
    )
    session = start_execution_session(artifact, req, backend.stores, ann_runner=ann)
    exec_result, _ = execute_request(session, backend.stores, ann_runner=ann)
    with backend.tx_factory() as tx:
        backend.stores.ledger.put_execution_result(tx, exec_result)
    assert exec_result.status.name == "PARTIAL"
    baseline_fp = exec_result.signature

    outcome = replay(
        req,
        artifact,
        backend.stores,
        ann_runner=ann,
        randomness=RandomnessProfile(seed=1, sources=("ann",), non_replayable=False),
        baseline_fingerprint=baseline_fp,
    )
    assert outcome.execution_contract is ExecutionContract.NON_DETERMINISTIC
    assert outcome.matches is False
    assert "results_fingerprint" in outcome.details
    assert ann.fallback_used
