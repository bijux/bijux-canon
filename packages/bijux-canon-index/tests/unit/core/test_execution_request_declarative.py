# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.errors import InvariantError
from bijux_canon_index.core.execution_intent import ExecutionIntent
from bijux_canon_index.core.execution_mode import ExecutionMode
from bijux_canon_index.core.types import (
    ExecutionArtifact,
    ExecutionRequest,
)
from bijux_canon_index.domain.requests.request_execution import start_execution_session
from bijux_canon_index.infra.adapters.memory.backend import memory_backend
import pytest


def test_execution_request_cannot_execute_directly() -> None:
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
        from bijux_canon_index.domain.requests.execution_plan import run_plan

        art = backend.stores.ledger.get_artifact("art")
        assert art is not None
        run_plan(
            plan=None,  # type: ignore[arg-type]
            execution=None,  # type: ignore[arg-type]
            artifact=art,
            resources=backend.stores,
        )
    # Session creation succeeds
    artifact = backend.stores.ledger.get_artifact("art")
    assert artifact is not None
    session = start_execution_session(
        artifact,
        request,
        backend.stores,
    )
    assert session.session_id
