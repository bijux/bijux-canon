# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Trace helpers for core logic."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from bijux_canon_reason.core.fingerprints import stable_id
from bijux_canon_reason.core.models.base import JsonValue, StableModel
from bijux_canon_reason.core.models.claims import Claim, EvidenceRef


class ToolDescriptor(StableModel):
    """Represents tool descriptor."""

    name: str
    version: str
    config_fingerprint: str


class RuntimeDescriptor(StableModel):
    """Represents runtime descriptor."""

    kind: str
    mode: Literal["live", "frozen"]
    tools: list[ToolDescriptor]


class ToolCall(StableModel):
    """Represents tool call."""

    id: str = ""
    tool_name: str
    arguments: dict[str, JsonValue] = Field(default_factory=dict)
    step_id: str
    call_idx: int

    @model_validator(mode="after")
    def _fill_id(self) -> ToolCall:
        """Handle fill ID."""
        if self.id:
            return self
        object.__setattr__(
            self,
            "id",
            stable_id(
                "call",
                {
                    "step_id": self.step_id or "",
                    "call_idx": self.call_idx or 0,
                    "tool": self.tool_name,
                    "args": self.arguments,
                },
            ),
        )
        return self


class ToolResult(StableModel):
    """Represents tool result."""

    call_id: str
    success: bool
    result: JsonValue | None = None
    error: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _alias_ok(cls, values: dict[str, object]) -> dict[str, object]:
        """Handle alias ok."""
        if isinstance(values, dict) and "ok" in values and "success" not in values:
            values["success"] = values.pop("ok")
        return values

    @property
    def ok(self) -> bool:
        """Handle ok."""
        return self.success


class UnderstandOutput(StableModel):
    """Represents understand output."""

    type: Literal["understand"] = Field(default="understand", alias="kind")
    normalized_question: str
    assumptions: list[str] = Field(default_factory=list)
    task_type: str = "generic"


class GatherOutput(StableModel):
    """Represents gather output."""

    type: Literal["gather"] = Field(default="gather", alias="kind")
    evidence_ids: list[str] = Field(default_factory=list)
    retrieval_queries: list[str] = Field(default_factory=list)
    retrieval_provenance: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _alias(cls, values: dict[str, object]) -> dict[str, object]:
        """Handle alias."""
        if (
            isinstance(values, dict)
            and "evidence_refs" in values
            and "evidence_ids" not in values
        ):
            values["evidence_ids"] = values.pop("evidence_refs")
        return values


class DeriveOutput(StableModel):
    """Represents derive output."""

    type: Literal["derive"] = Field(default="derive", alias="kind")
    claim_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _alias(cls, values: dict[str, object]) -> dict[str, object]:
        """Handle alias."""
        if (
            isinstance(values, dict)
            and "emitted_claim_ids" in values
            and "claim_ids" not in values
        ):
            values["claim_ids"] = values.pop("emitted_claim_ids")
        return values


class VerifyOutput(StableModel):
    """Represents verify output."""

    type: Literal["verify"] = Field(default="verify", alias="kind")
    validated_claim_ids: list[str] = Field(default_factory=list)
    rejected_claim_ids: list[str] = Field(default_factory=list)
    missing_support_claim_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _alias(cls, values: dict[str, object]) -> dict[str, object]:
        """Handle alias."""
        if (
            isinstance(values, dict)
            and "insufficient_support" in values
            and "missing_support_claim_ids" not in values
        ):
            values["missing_support_claim_ids"] = values.pop("insufficient_support")
        return values


class FinalizeOutput(StableModel):
    """Represents finalize output."""

    type: Literal["finalize"] = Field(default="finalize", alias="kind")
    final_claim_ids: list[str] = Field(default_factory=list)
    final_answer: str | None = None
    uncertainty: str | None = None


class InsufficientEvidenceOutput(StableModel):
    """Represents insufficient evidence output."""

    type: Literal["insufficient_evidence"] = Field(
        default="insufficient_evidence",
        alias="kind",
    )
    reason: str = "insufficient_evidence"
    retrieved: int = 0
    required: int = 0


StepOutput = Annotated[
    UnderstandOutput
    | GatherOutput
    | DeriveOutput
    | VerifyOutput
    | FinalizeOutput
    | InsufficientEvidenceOutput,
    Field(discriminator="type"),
]


class TraceEventKind(StrEnum):
    """Enumeration of trace event kind."""

    step_started = "step_started"
    step_finished = "step_finished"
    tool_called = "tool_called"
    tool_returned = "tool_returned"
    evidence_registered = "evidence_registered"
    claim_emitted = "claim_emitted"


class StepStartedEvent(StableModel):
    """Represents step started event."""

    kind: Literal[TraceEventKind.step_started] = TraceEventKind.step_started
    step_id: str = Field(min_length=1)
    idx: int | None = None

    @field_validator("step_id")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        """Handle non empty."""
        if value is None or str(value) == "":
            raise ValueError("step_id required")
        return value

    @model_validator(mode="before")
    @classmethod
    def _precheck(cls, values: dict[str, JsonValue]) -> dict[str, JsonValue]:
        """Handle precheck."""
        if values.get("step_id") is None:
            raise ValueError("step_id required")
        return values

    @model_validator(mode="after")
    def _check(self) -> StepStartedEvent:
        """Handle check."""
        if not self.step_id:
            raise ValueError("step_id required")
        return self


class StepFinishedEvent(StableModel):
    """Represents step finished event."""

    kind: Literal[TraceEventKind.step_finished] = TraceEventKind.step_finished
    step_id: str
    output: StepOutput
    idx: int | None = None


class ToolCalledEvent(StableModel):
    """Represents tool called event."""

    kind: Literal[TraceEventKind.tool_called] = TraceEventKind.tool_called
    step_id: str = Field(min_length=1)
    call: ToolCall
    idx: int | None = None

    @field_validator("step_id")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        """Handle non empty."""
        if value is None or str(value) == "":
            raise ValueError("step_id required")
        return value

    @model_validator(mode="before")
    @classmethod
    def _alias(cls, values: dict[str, object]) -> dict[str, object]:
        """Handle alias."""
        if isinstance(values, dict) and "tool_call" in values:
            values["call"] = values.pop("tool_call")
        return values

    @model_validator(mode="after")
    def _check(self) -> ToolCalledEvent:
        """Handle check."""
        if not isinstance(self.call, ToolCall):
            raise ValueError("call must be ToolCall")
        if not self.step_id:
            raise ValueError("step_id required")
        return self


class ToolReturnedEvent(StableModel):
    """Represents tool returned event."""

    kind: Literal[TraceEventKind.tool_returned] = TraceEventKind.tool_returned
    step_id: str = Field(min_length=1)
    result: ToolResult
    idx: int | None = None

    @field_validator("step_id")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        """Handle non empty."""
        if value is None or str(value) == "":
            raise ValueError("step_id required")
        return value

    @model_validator(mode="before")
    @classmethod
    def _alias(cls, values: dict[str, object]) -> dict[str, object]:
        """Handle alias."""
        if isinstance(values, dict) and "tool_result" in values:
            values["result"] = values.pop("tool_result")
        return values

    @model_validator(mode="after")
    def _check(self) -> ToolReturnedEvent:
        """Handle check."""
        if not isinstance(self.result, ToolResult):
            raise ValueError("result must be ToolResult")
        if not self.step_id:
            raise ValueError("step_id required")
        return self


class EvidenceRegisteredEvent(StableModel):
    """Represents evidence registered event."""

    kind: Literal[TraceEventKind.evidence_registered] = (
        TraceEventKind.evidence_registered
    )
    step_id: str = ""
    evidence: EvidenceRef
    idx: int | None = None


class ClaimEmittedEvent(StableModel):
    """Represents claim emitted event."""

    kind: Literal[TraceEventKind.claim_emitted] = TraceEventKind.claim_emitted
    step_id: str = Field(default="")
    claim: Claim
    idx: int | None = None


TraceEvent = Annotated[
    StepStartedEvent
    | StepFinishedEvent
    | ToolCalledEvent
    | ToolReturnedEvent
    | EvidenceRegisteredEvent
    | ClaimEmittedEvent,
    Field(discriminator="kind"),
]


class Trace(StableModel):
    """Represents trace."""

    id: str = ""
    runtime_protocol_version: int = 1
    schema_version: int = 1
    fingerprint_algo: str = "sha256"
    canonicalization_version: int = 1
    spec_id: str | None = None
    plan_id: str | None = None
    events: list[TraceEvent] = Field(default_factory=list)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    def with_content_id(self) -> Trace:
        """Handle with content ID."""
        cid = stable_id(
            "trace",
            {
                "events": [event.model_dump(mode="json") for event in self.events],
                "metadata": self.metadata,
                "spec_id": self.spec_id,
                "plan_id": self.plan_id,
                "runtime_protocol_version": self.runtime_protocol_version,
                "schema_version": self.schema_version,
                "fingerprint_algo": self.fingerprint_algo,
                "canonicalization_version": self.canonicalization_version,
            },
        )
        return self.model_copy(update={"id": cid})


__all__ = [
    "ClaimEmittedEvent",
    "DeriveOutput",
    "EvidenceRegisteredEvent",
    "FinalizeOutput",
    "GatherOutput",
    "InsufficientEvidenceOutput",
    "RuntimeDescriptor",
    "StepFinishedEvent",
    "StepOutput",
    "StepStartedEvent",
    "ToolCall",
    "ToolCalledEvent",
    "ToolDescriptor",
    "ToolResult",
    "ToolReturnedEvent",
    "Trace",
    "TraceEvent",
    "TraceEventKind",
    "UnderstandOutput",
    "VerifyOutput",
]
