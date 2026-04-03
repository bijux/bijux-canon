# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations
from bijux_canon_index.core.execution_intent import ExecutionIntent

import pytest

from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.interfaces.schemas.models import (
    ExplainRequest,
    ExecutionArtifactRequest,
    ExecutionBudgetPayload,
    IngestRequest,
    ExecutionRequestPayload,
)
from bijux_canon_index.core.errors import AuthzDeniedError
from bijux_canon_index.application.engine import VectorExecutionEngine


def test_read_only_blocks_mutations(monkeypatch):
    monkeypatch.setenv("BIJUX_CANON_INDEX_READ_ONLY", "1")
    orch = VectorExecutionEngine()
    with pytest.raises(AuthzDeniedError):
        orch.ingest(IngestRequest(documents=["hi"], vectors=[[0.0]]))
    with pytest.raises(AuthzDeniedError):
        orch.materialize(
            ExecutionArtifactRequest(execution_contract=ExecutionContract.DETERMINISTIC)
        )


def test_read_only_allows_reads(tmp_path, monkeypatch):
    db_path = str(tmp_path / "read-only.sqlite")
    monkeypatch.setenv("BIJUX_CANON_INDEX_STATE_PATH", db_path)
    setup = VectorExecutionEngine()
    setup.ingest(IngestRequest(documents=["hi"], vectors=[[0.0, 0.0]]))
    setup.materialize(
        ExecutionArtifactRequest(execution_contract=ExecutionContract.DETERMINISTIC)
    )

    monkeypatch.setenv("BIJUX_CANON_INDEX_READ_ONLY", "1")
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
