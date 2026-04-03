# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.execution_intent import ExecutionIntent

import pytest

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.types import ExecutionRequest, ExecutionBudget
from bijux_vex.domain.execution_requests.execute import start_execution_session
from bijux_vex.infra.adapters.memory.backend import memory_backend
from bijux_vex.core.types import ExecutionArtifact
from bijux_vex.core.errors import InvariantError


def test_execution_request_cannot_execute_directly():
    backend = memory_backend()
    with backend.tx_factory() as tx:
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
    request = ExecutionRequest(
        request_id="r1",
        text=None,
        vector=(0.0,),
        top_k=1,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
        execution_mode=ExecutionMode.STRICT,
    )
    with pytest.raises(InvariantError):
        # Direct run_plan without session should not be allowed
        from bijux_vex.domain.execution_requests.plan import run_plan

        art = backend.stores.ledger.get_artifact("art")
        run_plan(
            plan=None,  # type: ignore[arg-type]
            execution=None,  # type: ignore[arg-type]
            artifact=art,
            resources=backend.stores,
        )
    # Session creation succeeds
    session = start_execution_session(
        backend.stores.ledger.get_artifact("art"),
        request,
        backend.stores,
    )
    assert session.session_id
