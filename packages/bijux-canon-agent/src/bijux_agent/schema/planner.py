"""Schemas dedicated to planner execution plans."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import ConfigDict, Field

from bijux_agent.enums import AgentType
from bijux_agent.retrieval.interfaces import RetrievalRequest
from bijux_agent.schema.base import TypedBaseModel


class ExecutionPlan(TypedBaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    dag: Sequence[tuple[str, str]] = Field(..., description="List of directed edges")
    sequence: Sequence[AgentType] = Field(..., description="Ordered agent sequence")
    retrieval_steps: Sequence[RetrievalRequest] = Field(
        ..., description="Required retrieval requests"
    )
