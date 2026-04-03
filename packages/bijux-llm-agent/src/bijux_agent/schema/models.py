"""Strict Pydantic schemas for agent inputs, outputs, and runtime metadata."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Annotated, Any

from pydantic import ConfigDict, Field

from bijux_agent.constants import CONTRACT_VERSION
from bijux_agent.enums import (
    AgentStatus,
    AgentType,
    DecisionOutcome,
    ExecutionMode,
    FailureMode,
)
from bijux_agent.schema.base import TypedBaseModel


class AgentScore(TypedBaseModel):
    model_config = ConfigDict(
        frozen=True,
        str_strip_whitespace=True,
        extra="forbid",
    )

    label: Annotated[str, Field(min_length=1)]
    value: float = Field(..., ge=0.0, le=1.0)


class RunMetadata(TypedBaseModel):
    model_config = ConfigDict(
        frozen=True,
        str_strip_whitespace=True,
        extra="forbid",
    )

    run_id: Annotated[str, Field(min_length=1)]
    execution_mode: ExecutionMode = ExecutionMode.SYNC
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None
    status: AgentStatus = AgentStatus.PENDING


class AgentInput(TypedBaseModel):
    model_config = ConfigDict(
        frozen=True,
        str_strip_whitespace=True,
        extra="forbid",
    )

    task_goal: Annotated[str, Field(min_length=1)]
    payload: Mapping[str, Any] = Field(default_factory=dict)
    context_id: Annotated[str, Field(min_length=1)]
    metadata: Mapping[str, Any] = Field(default_factory=dict)
    agent_type: AgentType = AgentType.PLANNER
    execution_mode: ExecutionMode = ExecutionMode.SYNC


class AgentOutput(TypedBaseModel):
    model_config = ConfigDict(
        frozen=True,
        str_strip_whitespace=True,
        extra="forbid",
    )

    text: Annotated[str, Field(min_length=1)]
    artifacts: Mapping[str, Any] = Field(default_factory=dict)
    scores: Mapping[str, float] = Field(default_factory=dict)
    confidence: float = Field(..., ge=0.0, le=1.0)
    metadata: Mapping[str, Any] = Field(default_factory=dict)
    decision: DecisionOutcome = DecisionOutcome.PASS

    def model_post_init(self, __context: Any) -> None:
        for score in self.scores.values():
            if not 0.0 <= score <= 1.0:
                raise ValueError("Scores must be between 0 and 1")
        if self.metadata.get("contract_version") != CONTRACT_VERSION:
            raise ValueError(
                f"metadata must include contract_version={CONTRACT_VERSION}"
            )


class AgentError(TypedBaseModel):
    model_config = ConfigDict(
        frozen=True,
        str_strip_whitespace=True,
        extra="forbid",
    )

    code: FailureMode
    message: Annotated[str, Field(min_length=1)]
    details: str | None = None
    transient: bool = False
