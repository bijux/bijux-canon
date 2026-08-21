# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Closed contracts for structured provider synthesis and provenance."""

from __future__ import annotations

from enum import StrEnum
import re
from typing import Literal, Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.fingerprints import fingerprint_obj
from bijux_canon_reason.core.models.base import StableModel

_ARTIFACT_ID = re.compile(r"sha256:[0-9a-f]{64}")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def content_artifact_id(value: object) -> str:
    """Return a stable SHA-256 artifact identity."""

    return f"sha256:{fingerprint_obj(value)}"


def require_artifact_id(value: str) -> str:
    """Validate a SHA-256 artifact identity."""

    if _ARTIFACT_ID.fullmatch(value) is None:
        raise ValueError("artifact identity must be sha256:<64 lowercase hex>")
    return value


def require_sha256(value: str) -> str:
    """Validate a raw SHA-256 digest."""

    if _SHA256.fullmatch(value) is None:
        raise ValueError("digest must be 64 lowercase hex characters")
    return value


class CandidateOutcome(StrEnum):
    """Provider candidate disposition before deterministic verification."""

    answered = "answered"
    partial = "partial"
    abstained = "abstained"
    refused = "refused"


class CandidatePolarity(StrEnum):
    """Provider-proposed relationship between a claim and its evidence."""

    supports = "supports"
    opposes = "opposes"
    ambiguous = "ambiguous"


class StructuredCandidateClaim(StableModel):
    """One provider-proposed claim that remains unverified candidate data."""

    statement: str
    citation_evidence_artifact_ids: tuple[str, ...]
    polarity: CandidatePolarity
    qualifier: str | None
    scope: str

    @field_validator("statement", "scope")
    @classmethod
    def _validate_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("candidate claim text and scope must not be empty")
        return value

    @field_validator("qualifier")
    @classmethod
    def _validate_qualifier(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("candidate qualifier must be null or non-empty")
        return value

    @field_validator("citation_evidence_artifact_ids")
    @classmethod
    def _validate_citations(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or len(value) != len(set(value)):
            raise ValueError("candidate claims require unique citation identities")
        return tuple(require_artifact_id(item) for item in value)


class StructuredSynthesisCandidate(StableModel):
    """Strict provider response; never a verified grounded answer by itself."""

    schema_version: Literal["bijux.canon.reason.provider_synthesis_candidate.v1"]
    outcome: CandidateOutcome
    answer: str
    claims: tuple[StructuredCandidateClaim, ...]
    limitations: tuple[str, ...]
    conflicts: tuple[str, ...]
    assumptions: tuple[str, ...]

    @field_validator("answer")
    @classmethod
    def _validate_answer(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("provider candidate answer must not be empty")
        return value

    @field_validator("limitations", "conflicts", "assumptions")
    @classmethod
    def _validate_text_items(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("provider candidate list items must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_outcome(self) -> Self:
        if self.outcome in {CandidateOutcome.answered, CandidateOutcome.partial}:
            if not self.claims:
                raise ValueError("answered provider candidates require claims")
        elif self.claims:
            raise ValueError(
                "abstained or refused provider candidates cannot expose claims"
            )
        if self.outcome is CandidateOutcome.partial and not self.limitations:
            raise ValueError("partial provider candidates require limitations")
        return self


class ProviderAttemptKind(StrEnum):
    """Why one bounded provider request was issued."""

    initial = "initial"
    retry = "retry"
    repair = "repair"


class ProviderAttemptStatus(StrEnum):
    """Terminal status of one provider request attempt."""

    accepted = "accepted"
    refused = "refused"
    retryable_error = "retryable_error"
    rejected = "rejected"
    invalid_candidate = "invalid_candidate"


class ProviderAttemptReceipt(StableModel):
    """Secret-safe hashes, usage, and latency for one provider attempt."""

    attempt: int
    kind: ProviderAttemptKind
    status: ProviderAttemptStatus
    request_sha256: str
    response_sha256: str | None
    http_status: int | None
    duration_ms: int
    latency_sha256: str
    usage_sha256: str
    input_tokens: int | None
    output_tokens: int | None
    provider_request_id_sha256: str | None
    validation_error_codes: tuple[str, ...]

    @field_validator(
        "request_sha256",
        "latency_sha256",
        "usage_sha256",
    )
    @classmethod
    def _validate_required_hash(cls, value: str) -> str:
        return require_sha256(value)

    @field_validator("response_sha256", "provider_request_id_sha256")
    @classmethod
    def _validate_optional_hash(cls, value: str | None) -> str | None:
        return None if value is None else require_sha256(value)

    @model_validator(mode="after")
    def _validate_attempt(self) -> Self:
        if self.attempt <= 0 or self.duration_ms < 0:
            raise ValueError("provider attempt number and duration are invalid")
        if self.http_status is not None and not 100 <= self.http_status <= 599:
            raise ValueError("provider HTTP status is invalid")
        for token_count in (self.input_tokens, self.output_tokens):
            if token_count is not None and token_count < 0:
                raise ValueError("provider usage counts must not be negative")
        if any(not code for code in self.validation_error_codes):
            raise ValueError("provider validation error codes must not be empty")
        return self


class StructuredProviderSynthesis(StableModel):
    """Accepted provider candidate plus complete bounded request provenance."""

    schema_version: str = "bijux.canon.reason.structured_provider_synthesis.v1"
    artifact_id: str
    provider: str
    model: str
    endpoint_origin: str
    prompt_artifact_id: str
    prompt_version: str
    response_schema_sha256: str
    evidence_packet_artifact_id: str
    candidate: StructuredSynthesisCandidate
    attempts: tuple[ProviderAttemptReceipt, ...]

    @field_validator("artifact_id", "prompt_artifact_id", "evidence_packet_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("response_schema_sha256")
    @classmethod
    def _validate_schema_hash(cls, value: str) -> str:
        return require_sha256(value)

    @field_validator("provider", "model", "endpoint_origin", "prompt_version")
    @classmethod
    def _validate_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("provider provenance fields must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_result(self) -> Self:
        if not self.attempts or self.attempts[-1].status not in {
            ProviderAttemptStatus.accepted,
            ProviderAttemptStatus.refused,
        }:
            raise ValueError("provider synthesis requires a terminal accepted attempt")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("provider synthesis identity does not match its payload")
        return self


__all__ = [
    "CandidateOutcome",
    "CandidatePolarity",
    "ProviderAttemptKind",
    "ProviderAttemptReceipt",
    "ProviderAttemptStatus",
    "StructuredCandidateClaim",
    "StructuredProviderSynthesis",
    "StructuredSynthesisCandidate",
    "content_artifact_id",
    "require_artifact_id",
    "require_sha256",
]
