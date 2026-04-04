"""Schemas dedicated to planner execution plans."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import ConfigDict, Field

from bijux_canon_agent.contracts.base import TypedBaseModel
from bijux_canon_agent.contracts.retrieval import RetrievalRequest
from bijux_canon_agent.enums import AgentType


class ExecutionPlan(TypedBaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    dag: Sequence[tuple[str, str]] = Field(..., description="List of directed edges")
    sequence: Sequence[AgentType] = Field(..., description="Ordered agent sequence")
    retrieval_steps: Sequence[RetrievalRequest] = Field(
        ..., description="Required retrieval requests"
    )
