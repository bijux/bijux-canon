# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from bijux_vex.boundaries.pydantic_edges.models import (
    ExecutionArtifactRequest,
    ExecutionRequestPayload,
    IngestRequest,
)
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.services.execution_engine import VectorExecutionEngine


def test_deterministic_run_is_stable_across_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "state.sqlite"
    engine = VectorExecutionEngine(state_path=db_path)
    ingest = IngestRequest(
        documents=["alpha", "beta"],
        vectors=[[0.0, 0.0], [1.0, 1.0]],
    )
    engine.ingest(ingest)
    engine.materialize(
        ExecutionArtifactRequest(execution_contract=ExecutionContract.DETERMINISTIC)
    )
    payload = ExecutionRequestPayload(
        request_text=None,
        vector=(0.0, 0.0),
        top_k=1,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
    )
    first = engine.execute(payload)
    restarted = VectorExecutionEngine(state_path=db_path)
    second = restarted.execute(payload)
    assert first["results"] == second["results"]
