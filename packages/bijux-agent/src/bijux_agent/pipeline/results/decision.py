"""Structured decision artifacts produced by pipelines."""

from __future__ import annotations

from pydantic import ConfigDict, Field

from bijux_agent.enums import DecisionOutcome
from bijux_agent.schema.base import TypedBaseModel
from bijux_agent.utilities.final import final_class


@final_class
class DecisionArtifact(TypedBaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    """Captures why the pipeline arrived at its final verdict."""

    verdict: DecisionOutcome = Field(
        ..., description="Final verdict assigned by the pipeline"
    )
    justification: str = Field(
        ..., description="Human-readable summary of the decision rationale"
    )
    supporting_trace_ids: list[str] = Field(
        default_factory=list,
        description="References to trace entries or nodes that support the decision",
    )
