"""Contract models for agent inputs, outputs, and tracing."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field

from bijux_agent.constants import CONTRACT_VERSION
from bijux_agent.schema.base import TypedBaseModel
from bijux_agent.utilities.final import final_class


class AgentInputSchema(TypedBaseModel):
    """Represents the required input contract for every agent run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    task_goal: str = Field(..., description="Human goal in natural language")
    payload: Mapping[str, Any] = Field(
        default_factory=dict, description="Structured data"
    )
    context_id: str = Field(..., description="Unique traceable identifier")
    metadata: Mapping[str, Any] = Field(
        default_factory=dict, description="Optional hints"
    )


@final_class
class AgentOutputSchema(TypedBaseModel):
    """Defines normalized outputs with confidence and provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(..., description="Primary textual result")
    artifacts: Mapping[str, Any] = Field(
        default_factory=dict, description="Supplemental structured outputs"
    )
    scores: Mapping[str, float] = Field(
        default_factory=dict, description="Numeric judgments"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Mandatory confidence [0,1]"
    )
    metadata: Mapping[str, Any] = Field(
        default_factory=dict, description="Optional provenance data"
    )

    def model_post_init(self, __context: Any) -> None:
        if not self.text.strip():
            raise ValueError("Agent output text must contain at least some characters")
        if self.metadata.get("contract_version") != CONTRACT_VERSION:
            raise ValueError(
                f"metadata must include contract_version={CONTRACT_VERSION}"
            )

    # Guard mapping-style access to avoid ambiguity.
    def __getitem__(self, __key: str) -> Any:
        raise TypeError("AgentOutputSchema must be accessed through attributes only")

    def get(self, __key: str, __default: Any | None = None) -> Any:
        raise TypeError("AgentOutputSchema must be accessed through attributes only")


class AgentErrorSchema(TypedBaseModel):
    """Models structured errors emitted by agents."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(..., description="Machine-readable code")
    message: str = Field(..., description="Human-friendly explanation")
    details: str | None = Field(None, description="Optional diagnostic details")
    transient: bool = Field(
        False, description="Signals whether the orchestrator may retry"
    )


class AgentCallRecord(TypedBaseModel):
    """Captures a single agent call with inputs, outputs, and diagnostics."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    agent_id: str
    start_time: datetime
    end_time: datetime
    input: AgentInputSchema
    output: AgentOutputSchema | None
    error: AgentErrorSchema | None
    prompt_hash: str
    model_hash: str
    status: str = Field(..., description="success/failure/aborted")
