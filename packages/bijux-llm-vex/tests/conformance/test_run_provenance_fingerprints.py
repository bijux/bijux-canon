# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import json
from pathlib import Path

from bijux_vex.boundaries.pydantic_edges.models import (
    ExecutionArtifactRequest,
    ExecutionRequestPayload,
    IngestRequest,
)
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.services.execution_engine import VectorExecutionEngine


def test_run_metadata_includes_determinism_fingerprints(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("BIJUX_VEX_BACKEND", "memory")
    monkeypatch.setenv("BIJUX_VEX_RUN_DIR", str(tmp_path))
    engine = VectorExecutionEngine()
    engine.ingest(
        IngestRequest(documents=["hello"], vectors=[[0.1, 0.2]], correlation_id="req-1")
    )
    engine.materialize(
        ExecutionArtifactRequest(execution_contract=ExecutionContract.DETERMINISTIC)
    )
    engine.execute(
        ExecutionRequestPayload(
            request_text=None,
            vector=(0.1, 0.2),
            top_k=1,
            artifact_id="art-1",
            execution_contract=ExecutionContract.DETERMINISTIC,
            execution_intent=ExecutionIntent.EXACT_VALIDATION,
            execution_mode=ExecutionMode.STRICT,
            correlation_id="req-1",
        )
    )
    run_dirs = [p for p in tmp_path.iterdir() if p.is_dir()]
    assert len(run_dirs) == 1
    metadata = json.loads((run_dirs[0] / "metadata.json").read_text(encoding="utf-8"))
    fingerprints = metadata.get("determinism_fingerprints")
    assert isinstance(fingerprints, dict)
    assert "vectors" in fingerprints
    assert "config" in fingerprints
    assert "backend" in fingerprints
    assert "determinism" in fingerprints
