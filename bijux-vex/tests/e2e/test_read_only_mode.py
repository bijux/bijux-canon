# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.execution_intent import ExecutionIntent

import pytest

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.boundaries.pydantic_edges.models import (
    ExplainRequest,
    ExecutionArtifactRequest,
    ExecutionBudgetPayload,
    IngestRequest,
    ExecutionRequestPayload,
)
from bijux_vex.core.errors import AuthzDeniedError
from bijux_vex.services.execution_engine import VectorExecutionEngine


def test_read_only_blocks_mutations(monkeypatch):
    monkeypatch.setenv("BIJUX_VEX_READ_ONLY", "1")
    orch = VectorExecutionEngine()
    with pytest.raises(AuthzDeniedError):
        orch.ingest(IngestRequest(documents=["hi"], vectors=[[0.0]]))
    with pytest.raises(AuthzDeniedError):
        orch.materialize(
            ExecutionArtifactRequest(execution_contract=ExecutionContract.DETERMINISTIC)
        )


def test_read_only_allows_reads(monkeypatch):
    db_path = "read-only.sqlite"
    monkeypatch.setenv("BIJUX_VEX_STATE_PATH", db_path)
    setup = VectorExecutionEngine()
    setup.ingest(IngestRequest(documents=["hi"], vectors=[[0.0, 0.0]]))
    setup.materialize(
        ExecutionArtifactRequest(execution_contract=ExecutionContract.DETERMINISTIC)
    )

    monkeypatch.setenv("BIJUX_VEX_READ_ONLY", "1")
    orch = VectorExecutionEngine(state_path=db_path)
    search = orch.execute(
        ExecutionRequestPayload(
            request_text=None,
            vector=(0.0, 0.0),
            top_k=1,
            execution_contract=ExecutionContract.DETERMINISTIC,
            execution_intent=ExecutionIntent.EXACT_VALIDATION,
            execution_budget=ExecutionBudgetPayload(),
        )
    )
    assert "results" in search
    first = search["results"][0]
    explain = orch.explain(ExplainRequest(result_id=first))
    assert explain["vector_id"] == first
    replay = orch.replay("hi")
    assert "matches" in replay
