# SPDX-License-Identifier: MIT
# SPDX-License-Identifier: MIT
from __future__ import annotations
import pytest

from bijux_vex.core.errors import (
    InvariantError,
    NDExecutionUnavailableError,
    ValidationError,
)
from bijux_vex.core.execution_result import ApproximationReport
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    ExecutionBudget,
    ExecutionRequest,
    Vector,
)
from bijux_vex.domain.execution_requests.execute import (
    ExecutionOutcome,
    execute_request_outcome,
    start_execution_session,
)
from bijux_vex.domain.provenance.replay import replay
from bijux_vex.infra.adapters.ann_base import AnnExecutionRequestRunner
from bijux_vex.infra.adapters.memory.backend import memory_backend


class NoAnn(AnnExecutionRequestRunner):
    randomness_sources: tuple[str, ...] = ()
    reproducibility_bounds: str = "none"

    def approximate_request(self, artifact, request):
        return ()

    def approximation_report(self, artifact, request, results):
        return ApproximationReport(
            recall_at_k=0.0,
            rank_displacement=0.0,
            distance_error=0.0,
            algorithm="none",
            backend="memory",
            randomness_sources=self.randomness_sources,
            deterministic_fallback_used=False,
            algorithm_version="test",
            truncation_ratio=0.0,
        )


def _artifact(contract: ExecutionContract) -> tuple[ExecutionArtifact, any]:
    backend = memory_backend()
    with backend.tx_factory() as tx:
        doc = Document(document_id="d", text="t")
        backend.stores.vectors.put_document(tx, doc)
        chunk = Chunk(chunk_id="c", document_id="d", text="t", ordinal=0)
        backend.stores.vectors.put_chunk(tx, chunk)
        backend.stores.vectors.put_vector(
            tx, Vector(vector_id="v", chunk_id="c", values=(0.1,), dimension=1)
        )
        backend.stores.ledger.put_artifact(
            tx,
            ExecutionArtifact(
                artifact_id="a",
                corpus_fingerprint="corp",
                vector_fingerprint="vec",
                metric="l2",
                scoring_version="v1",
                execution_contract=contract,
            ),
        )
    return backend.stores.ledger.get_artifact("a"), backend


def test_nd_without_ann_runner_fails_loudly():
    artifact, backend = _artifact(ExecutionContract.NON_DETERMINISTIC)
    req = ExecutionRequest(
        request_id="r",
        text=None,
        vector=(0.0,),
        top_k=1,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
        execution_mode=ExecutionMode.BOUNDED,
        execution_budget=ExecutionBudget(max_ann_probes=1),
    )
    with pytest.raises(
        (InvariantError, ValidationError, NDExecutionUnavailableError)
    ) as exc:
        start_execution_session(artifact, req, backend.stores, ann_runner=None)
    assert "ann runner" in str(exc.value)


def test_budget_free_ann_probes_refused():
    artifact, backend = _artifact(ExecutionContract.NON_DETERMINISTIC)
    req = ExecutionRequest(
        request_id="r",
        text=None,
        vector=(0.0,),
        top_k=1,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
        execution_mode=ExecutionMode.BOUNDED,
        execution_budget=ExecutionBudget(max_ann_probes=0),
    )
    session = start_execution_session(artifact, req, backend.stores, ann_runner=NoAnn())
    outcome = execute_request_outcome(session, backend.stores, ann_runner=NoAnn())
    assert outcome.failure is not None or (
        outcome.result and outcome.result.status.name == "PARTIAL"
    )


def test_contract_mismatch_fails():
    artifact, backend = _artifact(ExecutionContract.DETERMINISTIC)
    req = ExecutionRequest(
        request_id="r",
        text=None,
        vector=(0.0,),
        top_k=1,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
        execution_mode=ExecutionMode.BOUNDED,
        execution_budget=ExecutionBudget(max_ann_probes=1),
    )
    with pytest.raises((InvariantError, ValidationError)):
        start_execution_session(artifact, req, backend.stores, ann_runner=NoAnn())


def test_replay_without_provenance_raises():
    artifact, backend = _artifact(ExecutionContract.DETERMINISTIC)
    req = ExecutionRequest(
        request_id="r",
        text=None,
        vector=(0.0,),
        top_k=1,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
        execution_mode=ExecutionMode.STRICT,
    )
    # Delete ledger entry to simulate missing provenance
    with backend.tx_factory() as tx:
        backend.stores.ledger.delete_artifact(tx, "a")
    with pytest.raises(InvariantError):
        replay(req, artifact, backend.stores)


def test_adversarial_violation_prioritizes_randomness_requirement():
    """Multiple contract violations should fail on the first, deterministic check."""
    artifact, backend = _artifact(ExecutionContract.NON_DETERMINISTIC)
    with pytest.raises(InvariantError) as exc:
        ExecutionRequest(
            request_id="r",
            text=None,
            vector=(0.0,),
            top_k=1,
            execution_contract=ExecutionContract.NON_DETERMINISTIC,
            execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
            execution_mode=ExecutionMode.STRICT,  # invalid for ND
            execution_budget=None,  # invalid
        )
    assert "non_deterministic executions require bounded or exploratory mode" in str(
        exc.value
    )
