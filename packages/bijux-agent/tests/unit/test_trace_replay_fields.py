from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.utils.trace_helpers import build_trace_header

from bijux_agent.constants import CONTRACT_VERSION
from bijux_agent.enums import DecisionOutcome
from bijux_agent.pipeline.control.phases import PipelinePhase
from bijux_agent.pipeline.definition import PipelineDefinition
from bijux_agent.pipeline.results.decision import DecisionArtifact
from bijux_agent.pipeline.tracing.trace_validator import TraceValidator
from bijux_agent.tracing import (
    ReplayMetadata,
    RunFingerprint,
    RunTraceHeader,
    TraceEntry,
)


def _definition() -> PipelineDefinition:
    return PipelineDefinition(
        name="test-replay",
        phases=[PipelinePhase.INIT, PipelinePhase.FINALIZE],
        terminal_phases={PipelinePhase.FINALIZE},
        allowed_transitions={PipelinePhase.INIT: {PipelinePhase.FINALIZE}},
    )


def _build_entries(
    *, missing_field: str | None = None
) -> tuple[list[TraceEntry], RunTraceHeader, PipelineDefinition]:
    definition = _definition()
    fingerprint = RunFingerprint.create(
        definition=definition,
        config={"mode": "replay-test"},
    )
    now = datetime(2025, 1, 1, tzinfo=UTC)
    init_entry = TraceEntry(
        agent_id="TEST",
        node="init",
        status="success",
        start_time=now,
        end_time=now,
        input={"phase": PipelinePhase.INIT.value},
        output={
            "artifacts": {},
            "metadata": {"contract_version": CONTRACT_VERSION},
            "scores": {"quality": 0.5},
        },
        scores={"quality": 0.5},
        prompt_hash="init",
        model_hash="model",
        phase=PipelinePhase.INIT.value,
        run_id="replay",
        replay_metadata=ReplayMetadata(),
        decision_artifact=None,
        run_fingerprint=None,
    )
    finalize_entry = TraceEntry(
        agent_id="ORCHESTRATOR",
        node="finalize",
        status="success",
        start_time=now,
        end_time=now,
        input={"phase": PipelinePhase.FINALIZE.value},
        output={
            "artifacts": {},
            "metadata": {"contract_version": CONTRACT_VERSION},
            "scores": {"quality": 0.9},
            "decision": DecisionOutcome.APPROVE.value,
        },
        scores={"quality": 0.9},
        prompt_hash="final",
        model_hash="model",
        phase=PipelinePhase.FINALIZE.value,
        run_id="replay",
        replay_metadata=ReplayMetadata(
            input_hash="hash",
            config_hash="config",
            model_id="model",
            convergence_hash="trace-hash",
        ),
        decision_artifact=DecisionArtifact(
            verdict=DecisionOutcome.APPROVE,
            justification="final",
            supporting_trace_ids=[],
        ),
        run_fingerprint=fingerprint,
    )
    entries = [init_entry, finalize_entry]
    if missing_field and missing_field != "run_fingerprint":
        setattr(finalize_entry, missing_field, "")
    if missing_field == "run_fingerprint":
        finalize_entry.run_fingerprint = None
    header = build_trace_header(
        runtime_version="replay-test",
        convergence_hash="trace-hash",
        convergence_reason="stability",
    )
    return entries, header, definition


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("prompt_hash", "prompt_hash"),
        ("model_hash", "model_hash"),
        ("run_fingerprint", "run_fingerprint"),
    ],
)
def test_replay_requires_critical_fields(field: str, message: str) -> None:
    entries, header, definition = _build_entries(missing_field=field)
    with pytest.raises(RuntimeError, match=message):
        TraceValidator.validate(
            entries, definition, stop_reason=None, semantics=None, header=header
        )


def test_replay_requires_convergence_hash() -> None:
    entries, header, definition = _build_entries()
    entries[-1].replay_metadata.convergence_hash = ""
    header.convergence_hash = ""
    with pytest.raises(RuntimeError, match="convergence_hash"):
        TraceValidator.validate(
            entries, definition, stop_reason=None, semantics=None, header=header
        )
