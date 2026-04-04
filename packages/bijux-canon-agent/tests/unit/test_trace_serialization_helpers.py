from __future__ import annotations

from datetime import UTC, datetime

from bijux_canon_agent.traces.trace import (
    ReplayMetadata,
    RunTrace,
    RunTraceHeader,
    TraceEntry,
)
from bijux_canon_agent.traces.trace_serialization import (
    serialize_run_trace,
    serialize_trace_entry,
)


def test_serialize_trace_entry_preserves_optional_fields() -> None:
    entry = TraceEntry(
        agent_id="reader",
        node="reader",
        status="ok",
        start_time=datetime(2024, 1, 1, tzinfo=UTC),
        end_time=datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC),
        input={"file_path": "note.txt"},
        output={"text": "hello"},
        replay_metadata=ReplayMetadata(model_id="m1"),
    )

    payload = serialize_trace_entry(entry)

    assert payload["agent_id"] == "reader"
    assert payload["output"] == {"text": "hello"}


def test_serialize_run_trace_serializes_entries() -> None:
    entry = TraceEntry(
        agent_id="reader",
        node="reader",
        status="ok",
        start_time=datetime(2024, 1, 1, tzinfo=UTC),
        end_time=datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC),
        input={"file_path": "note.txt"},
        replay_metadata=ReplayMetadata(model_id="m1"),
    )
    trace = RunTrace(
        run_id="run-1",
        header=RunTraceHeader(),
        entries=[entry],
    )

    payload = serialize_run_trace(trace)

    assert payload["run_id"] == "run-1"
    assert len(payload["entries"]) == 1
