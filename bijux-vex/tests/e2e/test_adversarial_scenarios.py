# SPDX-License-Identifier: MIT
# SPDX-License-Identifier: MIT
from __future__ import annotations
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.execution_intent import ExecutionIntent

import pytest

from bijux_vex.core.errors import BudgetExceededError, InvariantError
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


class ViolatingAnn(AnnExecutionRequestRunner):
    def __init__(self):
        self.used_fallback = False

    @property
    def randomness_sources(self) -> tuple[str, ...]:
        return ("ann_graph",)

    @property
    def reproducibility_bounds(self) -> str:
        return "unbounded"

    def deterministic_fallback(
        self, artifact_id, request
    ):  # pragma: no cover - specific path
        self.used_fallback = True
        return ()

    def approximate_request(self, artifact, request):
        # Return no results, forcing rank instability and divergence
        return ()

    def approximation_report(self, artifact, request, results):
        return ApproximationReport(
            recall_at_k=0.0,
            rank_displacement=0.0,
            distance_error=0.0,
            algorithm="violating-ann",
            backend="memory",
            randomness_sources=self.randomness_sources,
            deterministic_fallback_used=self.used_fallback,
            algorithm_version="test",
            truncation_ratio=0.0,
        )


class ExhaustingAnn(AnnExecutionRequestRunner):
    @property
    def randomness_sources(self) -> tuple[str, ...]:
        return ("ann_probe",)

    @property
    def reproducibility_bounds(self) -> str:
        return "bounded"

    def approximate_request(self, artifact, request):
        raise BudgetExceededError(
            message="ann probes exhausted",
            dimension="ann_probes",
            partial_results=(),
        )

    def approximation_report(self, artifact, request, results):
        return ApproximationReport(
            recall_at_k=0.0,
            rank_displacement=0.0,
            distance_error=0.0,
            algorithm="exhausting-ann",
            backend="memory",
            randomness_sources=self.randomness_sources,
            deterministic_fallback_used=False,
            algorithm_version="test",
            truncation_ratio=0.0,
        )


@pytest.fixture()
def backend_det():
    backend = memory_backend()
    with backend.tx_factory() as tx:
        backend.stores.vectors.put_document(tx, Document(document_id="d", text="t"))
        backend.stores.vectors.put_chunk(
            tx, Chunk(chunk_id="c", document_id="d", text="t", ordinal=0)
        )
        backend.stores.vectors.put_vector(
            tx,
            Vector(vector_id="v", chunk_id="c", values=(0.1,), dimension=1),
        )
        backend.stores.ledger.put_artifact(
            tx,
            ExecutionArtifact(
                artifact_id="art",
                corpus_fingerprint="corp",
                vector_fingerprint="vec",
                metric="l2",
                scoring_version="v1",
                execution_contract=ExecutionContract.DETERMINISTIC,
            ),
        )
    return backend


@pytest.fixture()
def backend_nd():
    backend = memory_backend()
    with backend.tx_factory() as tx:
        backend.stores.vectors.put_document(tx, Document(document_id="d", text="t"))
        backend.stores.vectors.put_chunk(
            tx, Chunk(chunk_id="c", document_id="d", text="t", ordinal=0)
        )
        backend.stores.vectors.put_vector(
            tx,
            Vector(vector_id="v", chunk_id="c", values=(0.1,), dimension=1),
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
        execution_intent=(
            ExecutionIntent.EXPLORATORY_SEARCH
            if contract is ExecutionContract.NON_DETERMINISTIC
            else ExecutionIntent.EXACT_VALIDATION
        ),
        execution_mode=(
            ExecutionMode.BOUNDED
            if contract is ExecutionContract.NON_DETERMINISTIC
            else ExecutionMode.STRICT
        ),
        execution_budget=budget,
    )


def _artifact(backend) -> ExecutionArtifact:
    art = backend.stores.ledger.get_artifact("art")
    if art is None:
        raise RuntimeError("artifact missing in fixture")
    return art


def test_budget_exhaustion_mid_execution_is_partial(backend_nd):
    ann = ExhaustingAnn()
    art = _artifact(backend_nd)
    req = _req(
        ExecutionContract.NON_DETERMINISTIC,
        budget=ExecutionBudget(max_vectors=5, max_ann_probes=1),
    )
    session = start_execution_session(art, req, backend_nd.stores, ann_runner=ann)
    result, _ = execute_request(session, backend_nd.stores, ann_runner=ann)
    assert result.status.name == "PARTIAL"


def test_ann_fallback_declared_bounds_violate(backend_nd):
    ann = ViolatingAnn()
    art = _artifact(backend_nd)
    req = _req(
        ExecutionContract.NON_DETERMINISTIC,
        budget=ExecutionBudget(max_vectors=2, max_ann_probes=2),
    )
    session = start_execution_session(art, req, backend_nd.stores, ann_runner=ann)
    result, _ = execute_request(session, backend_nd.stores, ann_runner=ann)
    assert result.status.name in {"PARTIAL", "SUCCESS"}
    # With no hits, overlap will diverge; enforce determinism report presence
    assert result.determinism_report is not None
    assert result.determinism_report.randomness_sources


def test_replay_refuses_with_provenance_when_contract_mismatch(backend_det):
    art = _artifact(backend_det)
    req = _req(ExecutionContract.DETERMINISTIC)
    session = start_execution_session(art, req, backend_det.stores)
    result, _ = execute_request(session, backend_det.stores)
    with backend_det.tx_factory() as tx:
        backend_det.stores.ledger.put_execution_result(tx, result)
    bad_req = _req(
        ExecutionContract.NON_DETERMINISTIC, budget=ExecutionBudget(max_ann_probes=1)
    )
    with pytest.raises(InvariantError):
        replay(bad_req, art, backend_det.stores)
