# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import ConfigDict, Field, model_validator

from bijux_canon_reason.core.models.base import JsonValue, StableModel
from bijux_canon_reason.core.models.claims import (
    Claim,
    ClaimStatus,
    ClaimType,
    EvidenceRef,
    SupportKind,
    SupportRef,
)
from bijux_canon_reason.core.models.planning import (
    Plan,
    PlanNode,
    ProblemSpec,
    StepKind,
    StepSpec,
    ToolRequest,
)
from bijux_canon_reason.core.models.trace import (
    ClaimEmittedEvent,
    DeriveOutput,
    EvidenceRegisteredEvent,
    FinalizeOutput,
    GatherOutput,
    InsufficientEvidenceOutput,
    RuntimeDescriptor,
    StepFinishedEvent,
    StepOutput,
    StepStartedEvent,
    ToolCall,
    ToolCalledEvent,
    ToolDescriptor,
    ToolResult,
    ToolReturnedEvent,
    Trace,
    TraceEvent,
    TraceEventKind,
    UnderstandOutput,
    VerifyOutput,
)


class VerificationSeverity(StrEnum):
    info = "info"
    warning = "warning"
    error = "error"


class VerificationPolicyMode(StrEnum):
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
