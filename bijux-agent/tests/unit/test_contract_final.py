"""Ensure the core contracts stay final at runtime."""

from __future__ import annotations

import pytest

from bijux_agent.models.contract import AgentOutputSchema
from bijux_agent.pipeline.results.outcome import PipelineResult


def test_agent_output_schema_is_final() -> None:
    with pytest.raises(TypeError):

        class _Bad(AgentOutputSchema):  # type: ignore
            pass


def test_pipeline_result_is_final() -> None:
    with pytest.raises(TypeError):

        class _BadResult(PipelineResult):  # type: ignore
            pass
