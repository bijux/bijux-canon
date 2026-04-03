from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, cast

from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError
import pytest
from tests.utils.trace_helpers import (
    build_replay_metadata,
    build_run_fingerprint,
    build_trace_header,
)

from bijux_agent.enums import DecisionOutcome
from bijux_agent.pipeline.control.stop_conditions import StopReason
from bijux_agent.pipeline.epistemic import EpistemicVerdict
from bijux_agent.pipeline.results.outcome import PipelineResult, PipelineStatus
from bijux_agent.tracing import RunTrace, TraceEntry
from bijux_agent.tracing.trace import ModelMetadata


def _validate_pipeline_result(data: dict[str, Any]) -> PipelineResult:
    validator = getattr(PipelineResult, "model_validate", None)
    if validator is None:
        raise AttributeError("PipelineResult.model_validate is unavailable")
    return cast(Callable[[dict[str, Any]], PipelineResult], validator)(data)


def _default_model_metadata() -> ModelMetadata:
    return ModelMetadata(
        provider="test-provider",
        model_name="test-model",
        temperature=0.0,
        max_tokens=512,
    )


def test_pipeline_result_roundtrip_serializes_cleanly() -> None:
    """PipelineResult should round-trip through model_dump/model_validate."""
    metadata = _default_model_metadata()
    original = PipelineResult(
        status=PipelineStatus.DONE,
        decision=DecisionOutcome.APPROVE,
        epistemic_verdict=EpistemicVerdict.CERTAIN,
        confidence=0.95,
        model_metadata=metadata,
    )
    serialized = original.model_dump()
    rehydrated = _validate_pipeline_result(serialized)
    assert isinstance(rehydrated, PipelineResult)
    assert rehydrated == original


@settings(database=None)
@given(
    confidence=st.one_of(
        st.floats(max_value=-0.01, allow_nan=False),
        st.floats(min_value=1.01, allow_nan=False),
    )
)
def test_pipeline_result_rejects_out_of_range_confidence(confidence: float) -> None:
    data = {
        "status": PipelineStatus.DONE,
        "decision": DecisionOutcome.APPROVE,
        "epistemic_verdict": EpistemicVerdict.CERTAIN,
        "confidence": confidence,
        "model_metadata": asdict(_default_model_metadata()),
    }
    with pytest.raises(ValidationError):
        _validate_pipeline_result(data)


@settings(database=None)
@given(status=st.text(min_size=1).filter(lambda s: s not in PipelineStatus.__members__))
def test_pipeline_result_rejects_unknown_status(status: str) -> None:
    data = {
        "status": status,
        "decision": DecisionOutcome.APPROVE,
        "epistemic_verdict": EpistemicVerdict.CERTAIN,
        "confidence": 0.75,
        "model_metadata": asdict(_default_model_metadata()),
    }
    with pytest.raises(ValidationError):
        _validate_pipeline_result(data)


def test_pipeline_result_from_trace_reconstructs_outcome() -> None:
    now = datetime(2024, 1, 1, tzinfo=UTC)
    entry = TraceEntry(
        agent_id="agent",
        node="node",
        status="success",
        start_time=now,
        end_time=now,
        input={"phase": "FINALIZE"},
        output={
            "text": "final result",
            "artifacts": {},
            "scores": {"quality": 0.95},
            "confidence": 0.65,
            "metadata": {"contract_version": "v0"},
            "decision": DecisionOutcome.VETO.value,
        },
        scores={"quality": 0.95},
        prompt_hash="hash",
        model_hash="model",
        phase="FINALIZE",
        run_id="trace-1",
        stop_reason=StopReason.USER_INTERRUPTION,
        replay_metadata=build_replay_metadata(),
        epistemic_verdict=EpistemicVerdict.UNCERTAIN,
        run_fingerprint=build_run_fingerprint(),
    )

    trace = RunTrace(
        run_id="trace-1",
        status="aborted",
        header=build_trace_header(convergence_reason="stability"),
    )
    trace.header.model_metadata = _default_model_metadata()
    trace.entries.append(entry)
    result = PipelineResult.from_trace(trace)

    assert result.status == PipelineStatus.ABORTED
    assert result.confidence == 0.65
    assert result.stop_reason == StopReason.USER_INTERRUPTION
    assert result.decision == DecisionOutcome.VETO
    assert result.epistemic_verdict == EpistemicVerdict.UNCERTAIN
