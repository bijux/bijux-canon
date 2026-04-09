"""Ensure the core contracts stay final at runtime."""

from __future__ import annotations

from bijux_canon_agent.contracts.agent_contract import AgentOutputSchema
from bijux_canon_agent.pipeline.results.outcome import PipelineResult
import pytest


def test_agent_output_schema_is_final() -> None:
    with pytest.raises(TypeError):

        class _Bad(AgentOutputSchema):  # type: ignore
            pass


def test_pipeline_result_is_final() -> None:
    with pytest.raises(TypeError):

        class _BadResult(PipelineResult):  # type: ignore
            pass
