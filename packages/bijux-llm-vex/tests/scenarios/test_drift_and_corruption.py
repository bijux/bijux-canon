# SPDX-License-Identifier: MIT
# SPDX-License-Identifier: MIT
from __future__ import annotations
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.execution_intent import ExecutionIntent

import pytest

from bijux_vex.core.errors import InvariantError
from bijux_vex.core.execution_result import ApproximationReport
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


class DriftAnn(AnnExecutionRequestRunner):
    def __init__(self, diverge_ratio: float = 0.1):
        self.diverge_ratio = diverge_ratio

    @property
    def randomness_sources(self) -> tuple[str, ...]:
        return ("ann_graph",)

    @property
    def reproducibility_bounds(self) -> str:
        return "bounded"

    def approximate_request(self, artifact, request):
        # Return empty result set to simulate drift within bounds
        return ()

    def approximation_report(self, artifact, request, results):
        return ApproximationReport(
            recall_at_k=0.0,
            rank_displacement=0.0,
            distance_error=0.0,
            algorithm="drift-ann",
            backend="memory",
            randomness_sources=self.randomness_sources,
            deterministic_fallback_used=False,
            algorithm_version="test",
            truncation_ratio=0.0,
        )


@pytest.fixture()
def backend_fixture():
    backend = memory_backend()
    with backend.tx_factory() as tx:
        backend.stores.vectors.put_document(tx, Document(document_id="d", text="t"))
        backend.stores.vectors.put_chunk(
            tx, Chunk(chunk_id="c", document_id="d", text="t", ordinal=0)
        )
        backend.stores.vectors.put_vector(
            tx, Vector(vector_id="v", chunk_id="c", values=(0.1,), dimension=1)
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


def _req(contract: ExecutionContract, budget: ExecutionBudget | None = None):
    return ExecutionRequest(
        request_id="r",
        text=None,
        vector=(0.0,),
        top_k=1,
        execution_contract=contract,
        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH
        if contract is ExecutionContract.NON_DETERMINISTIC
        else "exact_validation",
        execution_mode=ExecutionMode.BOUNDED
        if contract is ExecutionContract.NON_DETERMINISTIC
        else "strict",
        execution_budget=budget,
    )


def test_nd_drift_within_bounds_emits_report(backend_fixture):
    ann = DriftAnn()
    art = backend_fixture.stores.ledger.get_artifact("art")
    req = _req(
        ExecutionContract.NON_DETERMINISTIC,
        budget=ExecutionBudget(max_ann_probes=1, max_vectors=1),
    )
    session = start_execution_session(art, req, backend_fixture.stores, ann_runner=ann)
    result, _ = execute_request(session, backend_fixture.stores, ann_runner=ann)
    assert result.determinism_report is not None
    assert result.status.name in {"SUCCESS", "PARTIAL"}


def test_replay_fails_on_corrupted_artifact(backend_fixture):
    art = backend_fixture.stores.ledger.get_artifact("art")
    req = _req(
        ExecutionContract.NON_DETERMINISTIC, budget=ExecutionBudget(max_ann_probes=1)
    )
    session = start_execution_session(
        art, req, backend_fixture.stores, ann_runner=DriftAnn()
    )
    result, _ = execute_request(session, backend_fixture.stores, ann_runner=DriftAnn())
    with backend_fixture.tx_factory() as tx:
        backend_fixture.stores.ledger.put_execution_result(tx, result)
        # Corrupt artifact lineage
        backend_fixture.stores.ledger.delete_artifact(tx, art.artifact_id)
        with pytest.raises(InvariantError):
            replay(req, art, backend_fixture.stores, ann_runner=DriftAnn())
