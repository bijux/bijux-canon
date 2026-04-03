# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from bijux_canon_reason.core.models.base import JsonValue, StableModel


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

        normalized: list[VerificationFailure] = []
        for failure in failures:
            if isinstance(failure, VerificationFailure):
                normalized.append(failure)
            elif isinstance(failure, str):
                normalized.append(
                    VerificationFailure(
                        severity=VerificationSeverity.error,
                        message=failure,
                        invariant_id=None,
                    )
                )
        values["failures"] = normalized
        return values


class ReplayResult(StableModel):
    original_trace_fingerprint: str
    replayed_trace_fingerprint: str
    diff_summary: dict[str, JsonValue] = Field(default_factory=dict)


__all__ = [
    "ReplayResult",
    "VerificationCheck",
    "VerificationFailure",
    "VerificationPolicyMode",
    "VerificationReport",
    "VerificationSeverity",
]
