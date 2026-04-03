"""Helpers for classifying replay mismatches."""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Any

from bijux_agent.pipeline.results.outcome import PipelineResult


class ReplayMismatchCategory(str, Enum):
    CONFIG_DRIFT = "config drift"
    MODEL_DRIFT = "model drift"
    PROMPT_DRIFT = "prompt drift"
    NON_DETERMINISTIC_FIELD = "non-deterministic field"
    UNKNOWN = "unknown"


def classify_replay_mismatch(
    expected: Mapping[str, Any], actual: PipelineResult
) -> ReplayMismatchCategory:
    """Determine why replayed output deviates from the stored final result."""

    expected_verdict = expected.get("verdict")
    if expected_verdict and expected_verdict != actual.decision.value:
        return ReplayMismatchCategory.MODEL_DRIFT

    expected_confidence = float(expected.get("confidence", 0.0))
    if abs(expected_confidence - actual.confidence) > 1e-6:
        return ReplayMismatchCategory.PROMPT_DRIFT

    expected_stop = expected.get("stop_reason")
    actual_stop = actual.stop_reason.value if actual.stop_reason else None
    if expected_stop != actual_stop:
        return ReplayMismatchCategory.CONFIG_DRIFT

    expected_epistemic = expected.get("epistemic_status")
    if expected_epistemic != actual.epistemic_verdict.value:
        return ReplayMismatchCategory.NON_DETERMINISTIC_FIELD

    return ReplayMismatchCategory.UNKNOWN
