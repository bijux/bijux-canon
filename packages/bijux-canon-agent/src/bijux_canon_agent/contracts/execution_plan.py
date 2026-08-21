"""Schemas dedicated to planner execution plans."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from typing import Annotated, Any, Literal

from pydantic import ConfigDict, Field

from bijux_canon_agent.contracts.base import TypedBaseModel
from bijux_canon_agent.contracts.retrieval import RetrievalRequest
from bijux_canon_agent.enums import AgentType


class ProviderProfile(TypedBaseModel):
    """Immutable provider selection carried into a research plan."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    provider: Annotated[str, Field(min_length=1)]
    model: Annotated[str, Field(min_length=1)]
    immutable_revision: Annotated[str, Field(min_length=1)]
    temperature: float = Field(..., ge=0.0)
    seed: int | None = Field(default=None, ge=0)


class PlanningBudget(TypedBaseModel):
    """Complete resource ceiling for one research plan."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    iterations: int = Field(..., ge=1)
    retrievals: int = Field(..., ge=1)
    candidates: int = Field(..., ge=1)
    evidence_items: int = Field(..., ge=1)
    tool_calls: int = Field(..., ge=0)
    provider_calls: int = Field(..., ge=0)
    tokens: int = Field(..., ge=0)
    elapsed_ms: int = Field(..., ge=1)
    retries: int = Field(..., ge=0)
    artifact_bytes: int = Field(..., ge=1)

    def model_post_init(self, __context: Any) -> None:
        """Reject plans whose subordinate ceilings cannot satisfy retrieval."""
        if self.candidates < self.evidence_items:
            raise ValueError("candidates must be greater than or equal to evidence_items")
        if self.retrievals > self.tool_calls:
            raise ValueError("tool_calls must be greater than or equal to retrievals")


class ResearchPlanningInput(TypedBaseModel):
    """User and runtime inputs that determine a research plan."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    query: Annotated[str, Field(min_length=1)]
    corpus_generation: Annotated[str, Field(min_length=1)]
    index_generation: Annotated[str, Field(min_length=1)]
    scope: tuple[Annotated[str, Field(min_length=1)], ...] = Field(min_length=1)
    top_k: int = Field(..., ge=1, le=1000)
    retrieval_mode: Literal[
        "lexical", "dense_exact", "dense_approximate", "hybrid"
    ]
    constraints: Mapping[str, Any]
    provider_profile: ProviderProfile
    budget: PlanningBudget

    def model_post_init(self, __context: Any) -> None:
        """Keep requested retrieval work inside the declared budget."""
        if self.top_k > self.budget.candidates:
            raise ValueError("top_k must not exceed the candidate budget")
        if len(self.scope) != len(set(self.scope)):
            raise ValueError("scope entries must be unique")
        try:
            json.dumps(
                dict(self.constraints),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("constraints must be canonical JSON values") from exc


class ExecutionPlan(TypedBaseModel):
    """Deterministic execution graph bound to its complete planning inputs."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    planning_input: ResearchPlanningInput
    dag: Sequence[tuple[str, str]] = Field(..., description="List of directed edges")
    sequence: Sequence[AgentType] = Field(..., description="Ordered agent sequence")
    retrieval_steps: Sequence[RetrievalRequest] = Field(
        ..., description="Required retrieval requests"
    )
