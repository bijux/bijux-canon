from __future__ import annotations

from bijux_agent.enums import DecisionOutcome
from bijux_agent.pipeline.control.stop_conditions import StopReason
from bijux_agent.pipeline.epistemic import EpistemicVerdict
from bijux_agent.pipeline.results.outcome import PipelineResult, PipelineStatus
from bijux_agent.replay import (
    ReplayMismatchCategory,
    classify_replay_mismatch,
)
from bijux_agent.tracing.trace import ModelMetadata


def _default_model_metadata() -> ModelMetadata:
    return ModelMetadata(
        provider="test-provider",
        model_name="test-model",
        temperature=0.0,
        max_tokens=512,
    )


def _build_result(
    *,
    verdict: DecisionOutcome = DecisionOutcome.PASS,
    confidence: float = 0.5,
    epistemic: EpistemicVerdict = EpistemicVerdict.CERTAIN,
    stop_reason: StopReason | None = None,
) -> PipelineResult:
    metadata = _default_model_metadata()
    return PipelineResult(
        status=PipelineStatus.DONE,
        decision=verdict,
        epistemic_verdict=epistemic,
        confidence=confidence,
        stop_reason=stop_reason,
        model_metadata=metadata,
    )


def test_classify_mismatched_verdict() -> None:
    expected = {
        "verdict": DecisionOutcome.APPROVE.value,
        "confidence": 0.5,
        "epistemic_status": EpistemicVerdict.CERTAIN.value,
        "stop_reason": None,
    }
    actual = _build_result(verdict=DecisionOutcome.VETO)
    assert (
        classify_replay_mismatch(expected, actual) == ReplayMismatchCategory.MODEL_DRIFT
    )


def test_classify_mismatched_confidence() -> None:
    expected = {
        "verdict": DecisionOutcome.APPROVE.value,
        "confidence": 0.2,
        "epistemic_status": EpistemicVerdict.CERTAIN.value,
        "stop_reason": None,
    }
    actual = _build_result(confidence=0.8)
    assert (
        classify_replay_mismatch(expected, actual)
        == ReplayMismatchCategory.PROMPT_DRIFT
    )


def test_classify_stop_reason_differs() -> None:
    expected = {
        "verdict": DecisionOutcome.APPROVE.value,
        "confidence": 0.8,
        "epistemic_status": EpistemicVerdict.CERTAIN.value,
        "stop_reason": StopReason.MAX_ITERATIONS.value,
    }
    actual = _build_result(
        confidence=0.8,
        stop_reason=StopReason.USER_INTERRUPTION,
    )
    assert (
        classify_replay_mismatch(expected, actual)
        == ReplayMismatchCategory.CONFIG_DRIFT
    )


def test_classify_non_deterministic_fields() -> None:
    expected = {
        "verdict": DecisionOutcome.APPROVE.value,
        "confidence": 0.8,
        "epistemic_status": EpistemicVerdict.UNCERTAIN.value,
        "stop_reason": None,
    }
    actual = _build_result(
        confidence=0.8,
        epistemic=EpistemicVerdict.CERTAIN,
    )
    assert (
        classify_replay_mismatch(expected, actual)
        == ReplayMismatchCategory.NON_DETERMINISTIC_FIELD
    )


def test_classify_falls_back_to_unknown() -> None:
    expected = {
        "verdict": DecisionOutcome.APPROVE.value,
        "confidence": 0.75,
        "epistemic_status": EpistemicVerdict.CERTAIN.value,
        "stop_reason": None,
    }
    actual = _build_result(confidence=0.75)
    assert classify_replay_mismatch(expected, actual) == ReplayMismatchCategory.UNKNOWN
