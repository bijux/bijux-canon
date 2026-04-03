from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from tests.utils.trace_helpers import (
    build_replay_metadata,
    build_run_fingerprint,
    default_model_metadata,
)

from bijux_agent.constants import CONTRACT_VERSION
from bijux_agent.tracing import ReplayMetadata, TraceEntry, TraceRecorder


def test_run_id_propagates_to_trace_entries_and_final_output(tmp_path: Path) -> None:
    trace_path = tmp_path / "run_trace.json"
    recorder = TraceRecorder(
        run_id="run-42",
        path=trace_path,
        model_metadata=default_model_metadata(),
    )

    now = datetime.now(UTC)
    entry = TraceEntry(
        agent_id="agent",
        node="node",
        status="success",
        start_time=now,
        end_time=now,
        input={"phase": "PLAN"},
        output={
            "text": "result",
            "artifacts": {},
            "scores": {"confidence": 1.0},
            "confidence": 0.9,
            "metadata": {"contract_version": CONTRACT_VERSION},
        },
        scores={"confidence": 1.0},
        prompt_hash="plan-hash",
        model_hash="plan-model",
        run_id="run-42",
        replay_metadata=build_replay_metadata(
            input_hash="",
            config_hash="",
            model_id="",
        ),
        run_fingerprint=build_run_fingerprint(),
    )
    recorder.record_entry(entry)
    assert entry.run_id == "run-42"
    assert entry.replay_metadata.input_hash == ""
    assert entry.replay_metadata.config_hash == ""
    assert entry.replay_metadata.model_id == ""
    assert entry.failure_artifact is None

    recorder.finish(status="completed")

    data = json.loads(trace_path.read_text(encoding="utf-8"))
    assert data["run_id"] == "run-42"
    assert all(item.get("run_id") == "run-42" for item in data["entries"])
    assert data["config_hash"] == ""
    assert data["pipeline_definition_hash"] == ""
    assert data["agent_versions"] == {}
    assert data["replay_status"] == "NON_REPLAYABLE"
    assert data["runtime_version"]


def test_trace_header_metadata_persists(tmp_path: Path) -> None:
    trace_path = tmp_path / "header_trace.json"
    expected_versions = {"node_one": "v1.0", "node_two": "v2.5"}
    recorder = TraceRecorder(
        run_id="header-run",
        path=trace_path,
        config_hash="cfg-hash",
        pipeline_definition_hash="def-hash",
        agent_versions=expected_versions,
        model_metadata=default_model_metadata(),
    )
    recorder.finish(status="completed")

    data = json.loads(trace_path.read_text(encoding="utf-8"))
    assert data["config_hash"] == "cfg-hash"
    assert data["pipeline_definition_hash"] == "def-hash"
    assert data["agent_versions"] == expected_versions
    assert data["replay_status"] == "REPLAYABLE"
    assert data["runtime_version"]


def test_trace_replay_status_remains_replayable_with_metadata(tmp_path: Path) -> None:
    trace_path = tmp_path / "replayable.json"
    recorder = TraceRecorder(
        run_id="r",
        path=trace_path,
        model_metadata=default_model_metadata(),
    )
    entry = TraceEntry(
        agent_id="agent",
        node="node",
        status="success",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
        input={"phase": "PLAN"},
        output={
            "text": "result",
            "artifacts": {},
            "scores": {"confidence": 1.0},
            "confidence": 0.9,
            "metadata": {"contract_version": CONTRACT_VERSION},
        },
        scores={"confidence": 1.0},
        prompt_hash="",
        model_hash="",
        replay_metadata=ReplayMetadata(
            input_hash="ihash",
            config_hash="chash",
            model_id="model-id",
        ),
        run_id="r",
        run_fingerprint=build_run_fingerprint(),
    )
    recorder.record_entry(entry)
    recorder.finish(status="completed")

    data = json.loads(trace_path.read_text(encoding="utf-8"))
    assert data["replay_status"] == "REPLAYABLE"
    assert data["runtime_version"]


def test_trace_marked_non_replayable_when_metadata_missing(tmp_path: Path) -> None:
    trace_path = tmp_path / "non_replayable.json"
    recorder = TraceRecorder(
        run_id="nr",
        path=trace_path,
        model_metadata=default_model_metadata(),
    )
    entry = TraceEntry(
        agent_id="agent",
        node="node",
        status="success",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
        input={"phase": "PLAN"},
        output={
            "text": "result",
            "artifacts": {},
            "scores": {"confidence": 1.0},
            "confidence": 0.9,
            "metadata": {"contract_version": CONTRACT_VERSION},
        },
        scores={"confidence": 1.0},
        prompt_hash="",
        model_hash="",
        replay_metadata=ReplayMetadata(),
        run_id="nr",
        run_fingerprint=build_run_fingerprint(),
    )
    recorder.record_entry(entry)
    recorder.finish(status="completed")

    data = json.loads(trace_path.read_text(encoding="utf-8"))
    assert data["replay_status"] == "NON_REPLAYABLE"
    assert data["runtime_version"]
