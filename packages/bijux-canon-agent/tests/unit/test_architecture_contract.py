"""Ensure critical public shape stays stable across structural changes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import bijux_canon_agent
from bijux_canon_agent.models.contract import AgentOutputSchema
from bijux_canon_agent.pipeline.definition import standard_pipeline_definition
from bijux_canon_agent.tracing.trace import RunFingerprint, TraceEntry


def _load_snapshot() -> dict[str, object]:
    snapshot_path = (
        Path(__file__).resolve().parents[1] / "snapshots" / "architecture_contract.json"
    )
    return json.loads(snapshot_path.read_text(encoding="utf-8"))


def test_architecture_contract_matches_snapshot() -> None:
    snapshot = _load_snapshot()
    config = {"pipeline": {"parameters": {}}, "agents": ["file_reader", "stage_runner"]}
    fingerprint = RunFingerprint.create(standard_pipeline_definition(), config)
    public_imports = cast(list[str], list(bijux_canon_agent.__all__))
    actual = {
        "public_imports": sorted(public_imports),
        "run_fingerprint": fingerprint.fingerprint,
        "trace_entry_fields": sorted(TraceEntry.__annotations__.keys()),
        "agent_output_fields": sorted(
            getattr(AgentOutputSchema, "model_fields", {}).keys()
        ),
    }
    assert actual == snapshot
