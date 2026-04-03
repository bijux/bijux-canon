"""Ensure critical public shape stays stable after refactors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import bijux_agent
from bijux_agent.models.contract import AgentOutputSchema
from bijux_agent.pipeline.definition import standard_pipeline_definition
from bijux_agent.tracing.trace import RunFingerprint, TraceEntry


def _load_snapshot() -> dict[str, object]:
    snapshot_path = (
        Path(__file__).resolve().parents[1] / "snapshots" / "refactor_safety_net.json"
    )
    return json.loads(snapshot_path.read_text(encoding="utf-8"))


def test_refactor_safety_net_matches_snapshot() -> None:
    snapshot = _load_snapshot()
    config = {"pipeline": {"parameters": {}}, "agents": ["file_reader", "task_handler"]}
    fingerprint = RunFingerprint.create(standard_pipeline_definition(), config)
    public_imports = cast(list[str], list(bijux_agent.__all__))
    actual = {
        "public_imports": sorted(public_imports),
        "run_fingerprint": fingerprint.fingerprint,
        "trace_entry_fields": sorted(TraceEntry.__annotations__.keys()),
        "agent_output_fields": sorted(
            getattr(AgentOutputSchema, "model_fields", {}).keys()
        ),
    }
    assert actual == snapshot
