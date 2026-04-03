# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
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
from bijux_vex.infra.adapters.memory.backend import memory_backend
from bijux_vex.services.execution_engine import VectorExecutionEngine


def test_v01_golden_replay_output_is_bit_identical() -> None:
    fixtures = Path(__file__).resolve().parents[3] / "fixtures" / "v0_1_replay"
    input_payload = json.loads((fixtures / "input.json").read_text(encoding="utf-8"))
    vectors = json.loads((fixtures / "vectors.json").read_text(encoding="utf-8"))
    request_payload = json.loads(
        (fixtures / "execution_request.json").read_text(encoding="utf-8")
    )
    expected = json.loads(
        (fixtures / "expected_replay_output.json").read_text(encoding="utf-8")
    )

    backend = memory_backend()
    engine = VectorExecutionEngine(backend=backend)

    engine.ingest(
        IngestRequest(documents=input_payload["documents"], vectors=vectors["vectors"])
    )
    engine.materialize(
        ExecutionArtifactRequest(execution_contract=ExecutionContract.DETERMINISTIC)
    )
    engine.execute(
        ExecutionRequestPayload(
            artifact_id=request_payload["artifact_id"],
            request_text=request_payload.get("request_text"),
            vector=tuple(request_payload["vector"]),
            top_k=request_payload["top_k"],
            execution_contract=ExecutionContract.DETERMINISTIC,
            execution_intent=ExecutionIntent(request_payload["execution_intent"]),
            execution_mode=ExecutionMode(request_payload["execution_mode"]),
        )
    )
    replay = engine.replay(
        request_payload["request_text"], artifact_id=request_payload["artifact_id"]
    )
    if isinstance(replay.get("nondeterministic_sources"), tuple):
        replay["nondeterministic_sources"] = list(replay["nondeterministic_sources"])
    assert replay == expected
