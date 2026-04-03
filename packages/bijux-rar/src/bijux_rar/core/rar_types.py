# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from enum import Enum
from pathlib import PurePosixPath
import re
from typing import Annotated, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic import JsonValue as PydanticJsonValue

from bijux_rar.core.fingerprints import stable_id

JsonValue = PydanticJsonValue


class StableModel(BaseModel):
    # validate_default enforces validators even for generated defaults
    model_config = ConfigDict(
        frozen=True, extra="forbid", validate_default=True, populate_by_name=True
    )


class ProblemSpec(StableModel):
    id: str = ""
    description: str
    constraints: dict[str, JsonValue] = Field(default_factory=dict)
    expected_output_type: str = "Claim"
    expected: dict[str, JsonValue] | None = None
    version: int | None = None

    def with_content_id(self) -> ProblemSpec:
        cid = stable_id(
            "spec",
            {
                "description": self.description,
                "constraints": self.constraints,
                "expected_output_type": self.expected_output_type,
                "expected": self.expected,
                "version": self.version,
            },
        )
        return self.model_copy(update={"id": cid})

    @model_validator(mode="after")
    def _ensure_id(self) -> ProblemSpec:
        if not self.id:
            object.__setattr__(
                self,
                "id",
                stable_id(
                    "spec",
                    {
                        "description": self.description,
                        "constraints": self.constraints,
                        "expected_output_type": self.expected_output_type,
                        "expected": self.expected,
                        "version": self.version,
                    },
                ),
            )
        return self


StepKind = Literal["understand", "gather", "derive", "verify", "finalize"]


class ToolRequest(StableModel):
    tool_name: str
    arguments: dict[str, JsonValue] = Field(default_factory=dict)


class StepSpec(StableModel):
    kind: StepKind
    notes: str = ""
    tool_requests: list[ToolRequest] = Field(default_factory=list)


class PlanNode(StableModel):
    id: str = ""
    kind: StepKind
    dependencies: list[str] = Field(default_factory=list)
    step: StepSpec
    parameters: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _default_step(cls, values: dict[str, object]) -> dict[str, object]:
        if "step" not in values and "kind" in values:
            kind = cast(StepKind, values["kind"])
            values["step"] = StepSpec(kind=kind)
        return values

    @model_validator(mode="after")
    def _fill_id(self) -> PlanNode:
        if not self.id:
            object.__setattr__(
                self,
                "id",
                stable_id(
                    "node",
                    {
                        "kind": self.kind,
                        "deps": self.dependencies,
                        "params": self.parameters,
                        "step": self.step.model_dump(mode="json"),
                    },
                ),
            )
        return self


class Plan(StableModel):
    id: str = ""
    problem: str = ""
    spec_id: str
    nodes: list[PlanNode] = Field(default_factory=list)
    edges: list[tuple[str, str]] = Field(default_factory=list)

    def with_content_id(self) -> Plan:
        cid = stable_id(
            "plan",
            {
                "problem": self.problem,
                "spec_id": self.spec_id,
                "nodes": [n.model_dump(mode="json") for n in self.nodes],
                "edges": self.edges,
            },
        )
        return self.model_copy(update={"id": cid})


class ToolDescriptor(StableModel):
    name: str
    version: str
    config_fingerprint: str


class RuntimeDescriptor(StableModel):
    kind: str
    mode: Literal["live", "frozen"]
    tools: list[ToolDescriptor]


class ToolCall(StableModel):
    id: str = ""
    tool_name: str
    arguments: dict[str, JsonValue] = Field(default_factory=dict)
    step_id: str
    call_idx: int

    @model_validator(mode="after")
    def _fill_id(self) -> ToolCall:
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
    call_id: str
    success: bool
    result: JsonValue | None = None
    error: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _alias_ok(cls, values: dict[str, object]) -> dict[str, object]:
        if isinstance(values, dict) and "ok" in values and "success" not in values:
            values["success"] = values.pop("ok")
        return values

    @property
    def ok(self) -> bool:
        return self.success


class SupportKind(str, Enum):
    claim = "claim"
    evidence = "evidence"
    tool_call = "tool_call"


class SupportRef(StableModel):
    """Immutable support reference with mandatory span+hash."""

    kind: SupportKind
    ref_id: str
    span: tuple[int, int]
    snippet_sha256: str
    hash_algo: Literal["sha256"] = "sha256"

    model_config = ConfigDict(frozen=True)

    @field_validator("span")
    @classmethod
    def _validate_span(cls, v: tuple[int, int]) -> tuple[int, int]:
        s, e = int(v[0]), int(v[1])
        if s < 0 or e <= s:
            raise ValueError("span must satisfy 0 <= start < end")
        return (s, e)

    @field_validator("snippet_sha256")
    @classmethod
    def _validate_snippet_sha(cls, v: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", v):
            raise ValueError("snippet_sha256 must be 64 lowercase hex characters")
        return v


class ClaimStatus(str, Enum):
    proposed = "proposed"
    validated = "validated"
    rejected = "rejected"


class ClaimType(str, Enum):
    derived = "derived"
    observed = "observed"
    assumed = "assumed"


class Claim(StableModel):
    id: str = ""
    statement: str
    status: ClaimStatus = ClaimStatus.proposed
    confidence: float = 0.0
    supports: list[SupportRef] = Field(default_factory=list)
    claim_type: ClaimType = ClaimType.derived
    structured: dict[str, JsonValue] | None = None

    @model_validator(mode="before")
    @classmethod
    def _alias_supports(cls, values: dict[str, object]) -> dict[str, object]:
        if (
            isinstance(values, dict)
            and "support_refs" in values
            and "supports" not in values
        ):
            values["supports"] = values.pop("support_refs")
        return values

    def with_content_id(self) -> Claim:
        cid = stable_id(
            "claim",
            {
                "statement": self.statement,
                "status": self.status,
                "confidence": self.confidence,
                "supports": [s.model_dump(mode="json") for s in self.supports],
                "claim_type": self.claim_type,
                "structured": self.structured,
            },
        )
        return self.model_copy(update={"id": cid})

    @model_validator(mode="after")
    def _ensure_id(self) -> Claim:
        if not self.id:
            object.__setattr__(
                self,
                "id",
                stable_id(
                    "claim",
                    {
                        "statement": self.statement,
                        "status": self.status,
                        "confidence": self.confidence,
                        "supports": [s.model_dump(mode="json") for s in self.supports],
                        "claim_type": self.claim_type,
                        "structured": self.structured,
                    },
                ),
            )
        return self

    @property
    def support_refs(self) -> list[SupportRef]:
        return self.supports

    @property
    def content(self) -> dict[str, JsonValue]:
        return {"statement": self.statement}


class EvidenceRef(StableModel):
    id: str = ""
    uri: str
    sha256: str
    span: tuple[int, int]
    chunk_id: str
    content_path: str = ""

    @field_validator("span")
    @classmethod
    def _validate_span(cls, v: tuple[int, int]) -> tuple[int, int]:
        s, e = int(v[0]), int(v[1])
        if s < 0 or e <= s:
            raise ValueError("span must satisfy 0 <= start < end")
        return (s, e)

    @field_validator("chunk_id")
    @classmethod
    def _validate_chunk_id(cls, v: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", v):
            raise ValueError("chunk_id must be 64 lowercase hex characters")
        return v

    @field_validator("content_path")
    @classmethod
    def _safe_content_path(cls, v: str) -> str:
        """Reject hostile paths.

        Traces can be loaded from untrusted sources; evidence paths must be:
        - relative
        - POSIX-style (no backslashes)
        - free of traversal (no '..')
        - free of Windows drive prefixes (e.g., 'C:')
        """
        if v == "":
            return v
        if "\\" in v:
            raise ValueError("content_path must use POSIX separators ('/')")
        if v.startswith("/"):
            raise ValueError("content_path must be relative")
        if re.match(r"^[A-Za-z]:", v):
            raise ValueError("content_path must not include a drive prefix")

        p = PurePosixPath(v)
        if any(part == ".." for part in p.parts):
            raise ValueError("content_path must not contain '..'")
        if any(part == "" for part in p.parts):
            raise ValueError("content_path must not contain empty segments")
        return str(p)

    def with_content_id(self) -> EvidenceRef:
        cid = stable_id(
            "evidence",
            {
                "uri": self.uri,
                "sha256": self.sha256,
                "span": self.span,
                "chunk_id": self.chunk_id,
                "content_path": self.content_path,
            },
        )
        return self.model_copy(update={"id": cid})

    @model_validator(mode="after")
    def _ensure_id(self) -> EvidenceRef:
        if not self.id:
            object.__setattr__(
                self,
                "id",
                stable_id(
                    "evidence",
                    {
                        "uri": self.uri,
                        "sha256": self.sha256,
                        "span": self.span,
                        "chunk_id": self.chunk_id,
                        "content_path": self.content_path,
                    },
                ),
            )
        return self


class UnderstandOutput(StableModel):
    type: Literal["understand"] = Field(default="understand", alias="kind")
    normalized_question: str
    assumptions: list[str] = Field(default_factory=list)
    task_type: str = "generic"


class GatherOutput(StableModel):
    type: Literal["gather"] = Field(default="gather", alias="kind")
    evidence_ids: list[str] = Field(default_factory=list)
    retrieval_queries: list[str] = Field(default_factory=list)
    retrieval_provenance: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _alias(cls, values: dict[str, object]) -> dict[str, object]:
        if (
            isinstance(values, dict)
            and "evidence_refs" in values
            and "evidence_ids" not in values
        ):
            values["evidence_ids"] = values.pop("evidence_refs")
        return values


class DeriveOutput(StableModel):
    type: Literal["derive"] = Field(default="derive", alias="kind")
    claim_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _alias(cls, values: dict[str, object]) -> dict[str, object]:
        if (
            isinstance(values, dict)
            and "emitted_claim_ids" in values
            and "claim_ids" not in values
        ):
            values["claim_ids"] = values.pop("emitted_claim_ids")
        return values


class VerifyOutput(StableModel):
    type: Literal["verify"] = Field(default="verify", alias="kind")
    validated_claim_ids: list[str] = Field(default_factory=list)
    rejected_claim_ids: list[str] = Field(default_factory=list)
    missing_support_claim_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _alias(cls, values: dict[str, object]) -> dict[str, object]:
        if (
            isinstance(values, dict)
            and "insufficient_support" in values
            and "missing_support_claim_ids" not in values
        ):
            values["missing_support_claim_ids"] = values.pop("insufficient_support")
        return values


class FinalizeOutput(StableModel):
    type: Literal["finalize"] = Field(default="finalize", alias="kind")
    final_claim_ids: list[str] = Field(default_factory=list)
    final_answer: str | None = None
    uncertainty: str | None = None


class InsufficientEvidenceOutput(StableModel):
    type: Literal["insufficient_evidence"] = Field(
        default="insufficient_evidence", alias="kind"
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


class TraceEventKind(str, Enum):
    step_started = "step_started"
    step_finished = "step_finished"
    tool_called = "tool_called"
    tool_returned = "tool_returned"
    evidence_registered = "evidence_registered"
    claim_emitted = "claim_emitted"


class StepStartedEvent(StableModel):
    kind: Literal[TraceEventKind.step_started] = TraceEventKind.step_started
    step_id: str = Field(min_length=1)
    idx: int | None = None

    @field_validator("step_id")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if v is None or str(v) == "":
            raise ValueError("step_id required")
        return v

    @model_validator(mode="before")
    @classmethod
    def _precheck(cls, values: dict[str, JsonValue]) -> dict[str, JsonValue]:
        if values.get("step_id") is None:
            raise ValueError("step_id required")
        return values

    @model_validator(mode="after")
    def _check(self) -> StepStartedEvent:
        if not self.step_id:
            raise ValueError("step_id required")
        return self


class StepFinishedEvent(StableModel):
    kind: Literal[TraceEventKind.step_finished] = TraceEventKind.step_finished
    step_id: str
    output: StepOutput
    idx: int | None = None


class ToolCalledEvent(StableModel):
    kind: Literal[TraceEventKind.tool_called] = TraceEventKind.tool_called
    step_id: str = Field(min_length=1)
    call: ToolCall
    idx: int | None = None

    @field_validator("step_id")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if v is None or str(v) == "":
            raise ValueError("step_id required")
        return v

    @model_validator(mode="before")
    @classmethod
    def _alias(cls, values: dict[str, object]) -> dict[str, object]:
        if isinstance(values, dict) and "tool_call" in values:
            values["call"] = values.pop("tool_call")
        return values

    @model_validator(mode="after")
    def _check(self) -> ToolCalledEvent:
        if not isinstance(self.call, ToolCall):
            raise ValueError("call must be ToolCall")
        if not self.step_id:
            raise ValueError("step_id required")
        return self


class ToolReturnedEvent(StableModel):
    kind: Literal[TraceEventKind.tool_returned] = TraceEventKind.tool_returned
    step_id: str = Field(min_length=1)
    result: ToolResult
    idx: int | None = None

    @field_validator("step_id")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if v is None or str(v) == "":
            raise ValueError("step_id required")
        return v

    @model_validator(mode="before")
    @classmethod
    def _alias(cls, values: dict[str, object]) -> dict[str, object]:
        if isinstance(values, dict) and "tool_result" in values:
            values["result"] = values.pop("tool_result")
        return values

    @model_validator(mode="after")
    def _check(self) -> ToolReturnedEvent:
        if not isinstance(self.result, ToolResult):
            raise ValueError("result must be ToolResult")
        if not self.step_id:
            raise ValueError("step_id required")
        return self


class EvidenceRegisteredEvent(StableModel):
    kind: Literal[TraceEventKind.evidence_registered] = (
        TraceEventKind.evidence_registered
    )
    step_id: str = ""
    evidence: EvidenceRef
    idx: int | None = None


class ClaimEmittedEvent(StableModel):
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
        cid = stable_id(
            "trace",
            {
                "events": [e.model_dump(mode="json") for e in self.events],
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


class VerificationSeverity(str, Enum):
    info = "info"
    warning = "warning"
    error = "error"


class VerificationPolicyMode(str, Enum):
    strict = "strict"
    audit = "audit"
    permissive = "permissive"


class VerificationFailure(StableModel):
    severity: VerificationSeverity
    message: str
    invariant_id: str | None = None

    def __contains__(self, item: object) -> bool:
        try:
            return isinstance(item, str) and item in self.message
        except Exception:  # noqa: BLE001
            return False


class VerificationCheck(StableModel):
    name: str
    passed: bool
    details: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)


class VerificationReport(StableModel):
    id: str | None = None
    checks: list[VerificationCheck] = Field(default_factory=list)
    failures: list[VerificationFailure] = Field(default_factory=list)
    summary_metrics: dict[str, float] = Field(default_factory=dict)
    trace_id: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_failures(cls, values: dict[str, object]) -> dict[str, object]:
        failures = values.get("failures")
        if not isinstance(failures, list):
            return values

        new: list[VerificationFailure] = []
        for f in failures:
            if isinstance(f, VerificationFailure):
                new.append(f)
            elif isinstance(f, str):
                new.append(
                    VerificationFailure(
                        severity=VerificationSeverity.error,
                        message=f,
                        invariant_id=None,
                    )
                )
        values["failures"] = new
        return values


class ReplayResult(StableModel):
    original_trace_fingerprint: str
    replayed_trace_fingerprint: str
    diff_summary: dict[str, JsonValue] = Field(default_factory=dict)
