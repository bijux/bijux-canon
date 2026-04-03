"""Snapshot test for the TraceEntry dataclass schema."""

from __future__ import annotations

from bijux_agent.tracing.trace import TraceEntry

EXPECTED_TRACE_SCHEMA = {
    "FIELD_CLASSIFICATIONS": "ClassVar[dict[str, TraceFieldClassification]]",
    "agent_id": "str",
    "node": "str",
    "status": "str",
    "start_time": "datetime",
    "end_time": "datetime",
    "input": "dict[str, Any]",
    "output": "dict[str, Any] | None",
    "error": "dict[str, Any] | None",
    "scores": "dict[str, float]",
    "prompt_hash": "str",
    "model_hash": "str",
    "phase": "str | None",
    "run_id": "str | None",
    "stop_reason": "StopReason | None",
    "failure_artifact": "FailureArtifact | None",
    "replay_metadata": "ReplayMetadata",
    "epistemic_status": "EpistemicStatus | None",
    "epistemic_verdict": "EpistemicVerdict | None",
    "decision_artifact": "DecisionArtifact | None",
    "run_fingerprint": "RunFingerprint | None",
    "termination_reason": "ExecutionTerminationReason | None",
}


def test_trace_entry_schema_matches_snapshot() -> None:
    """Detect when trace fields or types drift without an update."""
    actual = {
        name: str(field.type) for name, field in TraceEntry.__dataclass_fields__.items()
    }
    assert actual == EXPECTED_TRACE_SCHEMA
