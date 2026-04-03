# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.execution_intent import ExecutionIntent

import pytest
from typer.testing import CliRunner

from bijux_vex.boundaries.cli import app as cli_app
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import (
    BackendDivergenceError,
    InvariantError,
    NDExecutionUnavailableError,
    ValidationError,
)
from bijux_vex.core.failures import retry_with_policy
from bijux_vex.core.types import ExecutionArtifact, ExecutionBudget, ExecutionRequest
from bijux_vex.domain.execution_requests.execute import (
    execute_request,
    start_execution_session,
)
from bijux_vex.domain.monitoring.divergence import detect_backend_drift
from bijux_vex.domain.provenance.replay import replay
from bijux_vex.infra.adapters.memory.backend import memory_backend


def test_cli_help_snapshot():
    runner = CliRunner()
    result = runner.invoke(cli_app.app, ["--help"], prog_name="bijux")
    assert result.exit_code == 0
    assert "bijux" in result.output
    assert "execute" in result.output


def test_invariant_violation_replay_fail():
    backend = memory_backend()
    artifact = ExecutionArtifact(
        artifact_id="art",
        corpus_fingerprint="c",
        vector_fingerprint="v",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
    )
    request = ExecutionRequest(
        request_id="r",
        text=None,
        vector=(0.0,),
        top_k=1,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
        execution_mode=ExecutionMode.BOUNDED,
        execution_budget=ExecutionBudget(
            max_latency_ms=1, max_memory_mb=1, max_error=1.0
        ),
    )
    with pytest.raises(InvariantError):
        replay(request, artifact, backend.stores)


def test_backend_drift_detection_failure():
    backend = memory_backend()
    backend = backend._replace(ann=None)  # type: ignore[attr-defined]
    artifact = ExecutionArtifact(
        artifact_id="art",
        corpus_fingerprint="c",
        vector_fingerprint="v",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
    )
    with backend.tx_factory() as tx:
        backend.stores.ledger.put_artifact(tx, artifact)
    request = ExecutionRequest(
        request_id="r",
        text=None,
        vector=(0.0,),
        top_k=1,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
        execution_mode=ExecutionMode.BOUNDED,
        execution_budget=ExecutionBudget(
            max_latency_ms=1, max_memory_mb=1, max_error=1.0
        ),
    )
    with pytest.raises((InvariantError, ValidationError, NDExecutionUnavailableError)):
        detect_backend_drift(
            artifact_id="art",
            request=request,
            resources_a=backend.stores,
            resources_b=backend.stores,
            ann_runner_a=None,
            ann_runner_b=None,
        )


def test_nd_failure_propagates_with_retry_and_metadata():
    backend = memory_backend()._replace(ann=None)  # type: ignore[attr-defined]
    artifact = ExecutionArtifact(
        artifact_id="art",
        corpus_fingerprint="corp",
        vector_fingerprint="vec",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
    )
    with backend.tx_factory() as tx:
        backend.stores.ledger.put_artifact(tx, artifact)
    attempts = {"n": 0}

    def attempt():
        attempts["n"] += 1
        req = ExecutionRequest(
            request_id="r",
            text=None,
            vector=(0.0, 0.0),
            top_k=1,
            execution_contract=ExecutionContract.NON_DETERMINISTIC,
            execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
            execution_mode=ExecutionMode.BOUNDED,
            execution_budget=ExecutionBudget(
                max_latency_ms=1, max_memory_mb=1, max_error=1.0
            ),
        )
        session = start_execution_session(
            artifact, req, backend.stores, ann_runner=backend.ann
        )
        execute_request(session, backend.stores, ann_runner=backend.ann)

    with pytest.raises(NDExecutionUnavailableError):
        retry_with_policy(
            attempt, attempts=2, contract=ExecutionContract.NON_DETERMINISTIC
        )
    assert attempts["n"] == 1
