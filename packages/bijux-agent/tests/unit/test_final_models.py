"""Ensure core models remain final."""

from __future__ import annotations

from typing import Any

import pytest

from bijux_agent.models.contract import AgentOutputSchema
from bijux_agent.pipeline.results.decision import DecisionArtifact
from bijux_agent.pipeline.results.failure import FailureArtifact
from bijux_agent.pipeline.results.outcome import PipelineResult


def _assert_cannot_subclass(cls: type[Any]) -> None:
    with pytest.raises(TypeError):

        class _Bad(cls):  # type: ignore
            pass


def test_agent_output_schema_is_final() -> None:
    _assert_cannot_subclass(AgentOutputSchema)


def test_pipeline_result_is_final() -> None:
    _assert_cannot_subclass(PipelineResult)


def test_decision_artifact_is_final() -> None:
    _assert_cannot_subclass(DecisionArtifact)


def test_failure_artifact_is_final() -> None:
    _assert_cannot_subclass(FailureArtifact)
