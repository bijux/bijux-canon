from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from tests.utils.trace_helpers import (
    build_replay_metadata,
    build_run_fingerprint,
    build_trace_header,
)

from bijux_agent.enums import AgentType
from bijux_agent.pipeline.control.phases import PipelinePhase
from bijux_agent.pipeline.definition import standard_pipeline_definition
from bijux_agent.pipeline.tracing.trace_validator import TraceValidator
from bijux_agent.tracing.trace import TraceEntry


def _base_entry(
    *,
    phase: PipelinePhase,
    start: datetime,
    agent_type: AgentType | None = None,
) -> TraceEntry:
    payload = {
        "phase": phase.value,
    }
    if agent_type:
        payload["agent_type"] = agent_type.value
    return TraceEntry(
        agent_id="agent",
        node=f"{phase.value.lower()}_node",
        status="success",
        start_time=start,
        end_time=start,
        input=payload,
        output={"artifacts": {}, "metadata": {}, "scores": {"quality": 1}},
        scores={"quality": 1},
        prompt_hash=f"{phase.value.lower()}-hash",
        model_hash="model-hash",
        phase=phase.value,
        run_id="order-run",
        replay_metadata=build_replay_metadata(model_id="agent"),
        run_fingerprint=build_run_fingerprint(),
    )


def test_trace_requires_phase_timestamp_ordering() -> None:
    base = datetime(2025, 1, 1, tzinfo=UTC)
    first_execute = _base_entry(
        phase=PipelinePhase.EXECUTE,
        start=base,
        agent_type=AgentType.TASKHANDLER,
    )
    second_execute = _base_entry(
        phase=PipelinePhase.EXECUTE,
        start=base - timedelta(seconds=5),
        agent_type=AgentType.TASKHANDLER,
    )
    entries = [first_execute, second_execute]

    with pytest.raises(RuntimeError, match="strictly ordered"):
        TraceValidator.validate(
            entries,
            standard_pipeline_definition(),
            None,
            None,
            build_trace_header(convergence_reason="stability"),
        )


def test_deterministic_snapshot_excludes_timestamps() -> None:
    entry = _base_entry(
        phase=PipelinePhase.EXECUTE,
        start=datetime(2025, 1, 1, tzinfo=UTC),
        agent_type=AgentType.TASKHANDLER,
    )
    snapshot = entry.deterministic_snapshot()

    assert "start_time" not in snapshot
    assert "end_time" not in snapshot
    assert snapshot["agent_id"] == entry.agent_id
