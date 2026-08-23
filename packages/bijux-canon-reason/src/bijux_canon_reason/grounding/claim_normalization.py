# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Normalize synthesis candidates into exact-span atomic claims."""

from __future__ import annotations

from enum import StrEnum
import hashlib
import re
from typing import Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.extractive_synthesis import (
    CredentialFreeSynthesis,
    SynthesisOutcome,
)
from bijux_canon_reason.grounding.provider_contracts import (
    CandidateOutcome,
    CandidatePolarity,
    StructuredProviderSynthesis,
    content_artifact_id,
    require_artifact_id,
    require_sha256,
)

_INDEPENDENT_VERB = (
    r"(?:are|can|cannot|could|decreased|did|failed|found|had|has|have|increased|"
    r"is|may|might|remained|reported|showed|was|were|will|would)"
)
_BOUNDARY = re.compile(
    r"(?<=[.!?])\s+|;\s*|,\s+(?:but|whereas|while)\s+|"
    rf"\s+and\s+(?=(?:(?:the|this|these|no)\s+)?[^\W_]+\s+{_INDEPENDENT_VERB}\b)",
    flags=re.IGNORECASE,
)
_WORD = re.compile(r"[^\W_]+", flags=re.UNICODE)


class AtomicClaimPolarity(StrEnum):
    """Normalized candidate polarity before entailment verification."""

    supports = "supports"
    opposes = "opposes"
    ambiguous = "ambiguous"
    observed = "observed"


class ClaimConfidenceBasis(StrEnum):
    """Why an unverified normalized claim has its candidate status."""

    exact_extractive_span = "exact_extractive_span"
    structured_provider_candidate = "structured_provider_candidate"


class ClaimNormalizationOutcome(StrEnum):
    """Whether normalized claims exist for a synthesis."""

    claims_extracted = "claims_extracted"
    no_claims = "no_claims"


class ClaimNormalizationErrorCode(StrEnum):
    """Stable fail-closed claim normalization errors."""

    answer_span_missing = "answer_span_missing"
    answer_span_ambiguous = "answer_span_ambiguous"
    candidate_not_falsifiable = "candidate_not_falsifiable"


class ClaimNormalizationError(ValueError):
    """A synthesis claim cannot be bound to an exact answer span."""

    def __init__(self, code: ClaimNormalizationErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class AtomicClaim(StableModel):
    """One falsifiable candidate claim with exact answer coordinates."""

    artifact_id: str
    ordinal: int
    statement: str
    statement_sha256: str
    answer_span: tuple[int, int]
    answer_quote: str
    answer_quote_sha256: str
    qualifier: str | None
    scope: str
    polarity: AtomicClaimPolarity
    confidence_basis: ClaimConfidenceBasis
    citation_evidence_artifact_ids: tuple[str, ...]
    source_candidate_ordinal: int
    atomicity_basis: str

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("statement_sha256", "answer_quote_sha256")
    @classmethod
    def _validate_sha256(cls, value: str) -> str:
        return require_sha256(value)

    @field_validator("statement", "answer_quote", "scope", "atomicity_basis")
    @classmethod
    def _validate_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("atomic claim fields must not be empty")
        return value

    @field_validator("citation_evidence_artifact_ids")
    @classmethod
    def _validate_citations(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or len(value) != len(set(value)):
            raise ValueError("atomic claims require unique citation identities")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_claim(self) -> Self:
        if self.ordinal <= 0 or self.source_candidate_ordinal <= 0:
            raise ValueError("atomic claim ordinals must be positive")
        if self.answer_span[0] < 0 or self.answer_span[1] <= self.answer_span[0]:
            raise ValueError("atomic claim answer span must be non-empty and ordered")
        if self.statement != self.answer_quote:
            raise ValueError(
                "normalized statement must preserve the exact answer quote"
            )
        if hashlib.sha256(self.statement.encode()).hexdigest() != self.statement_sha256:
            raise ValueError("atomic claim statement hash does not match")
        if hashlib.sha256(self.answer_quote.encode()).hexdigest() != (
            self.answer_quote_sha256
        ):
            raise ValueError("atomic claim answer quote hash does not match")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("atomic claim identity does not match its payload")
        return self


class NormalizedClaimSet(StableModel):
    """Content-addressed atomic claims for one immutable synthesis answer."""

    schema_version: str = "bijux.canon.reason.normalized_claim_set.v1"
    artifact_id: str
    source_synthesis_artifact_id: str
    answer_text_sha256: str
    outcome: ClaimNormalizationOutcome
    claims: tuple[AtomicClaim, ...]

    @field_validator("artifact_id", "source_synthesis_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("answer_text_sha256")
    @classmethod
    def _validate_answer_hash(cls, value: str) -> str:
        return require_sha256(value)

    @model_validator(mode="after")
    def _validate_claim_set(self) -> Self:
        if self.outcome is ClaimNormalizationOutcome.claims_extracted:
            if not self.claims:
                raise ValueError("claims_extracted outcome requires atomic claims")
        elif self.claims:
            raise ValueError("no_claims outcome cannot expose atomic claims")
        if tuple(claim.ordinal for claim in self.claims) != tuple(
            range(1, len(self.claims) + 1)
        ):
            raise ValueError("atomic claim ordinals must be contiguous")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("normalized claim set identity does not match its payload")
        return self


class _ClaimInput(StableModel):
    statement: str
    qualifier: str | None
    scope: str
    polarity: AtomicClaimPolarity
    confidence_basis: ClaimConfidenceBasis
    citation_evidence_artifact_ids: tuple[str, ...]


class AtomicClaimNormalizer:
    """Split, bind, and preserve every candidate assertion without collapsing it."""

    def normalize_credential_free(
        self, synthesis: CredentialFreeSynthesis
    ) -> NormalizedClaimSet:
        """Normalize deterministic extractive points into exact-span claims."""

        inputs = tuple(
            _ClaimInput(
                statement=point.quote,
                qualifier="reported by the identified source",
                scope=point.source_id,
                polarity=AtomicClaimPolarity.observed,
                confidence_basis=ClaimConfidenceBasis.exact_extractive_span,
                citation_evidence_artifact_ids=(point.citation_evidence_artifact_id,),
            )
            for point in synthesis.points
        )
        if synthesis.outcome is SynthesisOutcome.insufficient:
            inputs = ()
        return self._normalize(
            source_synthesis_artifact_id=synthesis.artifact_id,
            answer_text=synthesis.answer_text,
            candidates=inputs,
        )

    def normalize_provider(
        self, synthesis: StructuredProviderSynthesis
    ) -> NormalizedClaimSet:
        """Normalize strict provider claims only when they occur in the answer."""

        inputs = tuple(
            _ClaimInput(
                statement=claim.statement,
                qualifier=claim.qualifier,
                scope=claim.scope,
                polarity=_provider_polarity(claim.polarity),
                confidence_basis=ClaimConfidenceBasis.structured_provider_candidate,
                citation_evidence_artifact_ids=(claim.citation_evidence_artifact_ids),
            )
            for claim in synthesis.candidate.claims
        )
        if synthesis.candidate.outcome in {
            CandidateOutcome.abstained,
            CandidateOutcome.refused,
        }:
            inputs = ()
        return self._normalize(
            source_synthesis_artifact_id=synthesis.artifact_id,
            answer_text=synthesis.candidate.answer,
            candidates=inputs,
        )

    def _normalize(
        self,
        *,
        source_synthesis_artifact_id: str,
        answer_text: str,
        candidates: tuple[_ClaimInput, ...],
    ) -> NormalizedClaimSet:
        claims: list[AtomicClaim] = []
        for candidate_ordinal, candidate in enumerate(candidates, start=1):
            candidate_start = _unique_span(answer_text, candidate.statement)
            for statement, relative_start, relative_end, basis in _atomic_segments(
                candidate.statement
            ):
                if not _is_falsifiable(statement):
                    raise ClaimNormalizationError(
                        ClaimNormalizationErrorCode.candidate_not_falsifiable,
                        "candidate claim is not a falsifiable assertion",
                    )
                start = candidate_start + relative_start
                end = candidate_start + relative_end
                assert answer_text[start:end] == statement
                ordinal = len(claims) + 1
                payload = {
                    "ordinal": ordinal,
                    "statement": statement,
                    "statement_sha256": hashlib.sha256(statement.encode()).hexdigest(),
                    "answer_span": (start, end),
                    "answer_quote": statement,
                    "answer_quote_sha256": hashlib.sha256(
                        statement.encode()
                    ).hexdigest(),
                    "qualifier": candidate.qualifier,
                    "scope": candidate.scope,
                    "polarity": candidate.polarity.value,
                    "confidence_basis": candidate.confidence_basis.value,
                    "citation_evidence_artifact_ids": candidate.citation_evidence_artifact_ids,
                    "source_candidate_ordinal": candidate_ordinal,
                    "atomicity_basis": basis,
                }
                claims.append(
                    AtomicClaim(
                        artifact_id=content_artifact_id(payload),
                        ordinal=ordinal,
                        statement=statement,
                        statement_sha256=hashlib.sha256(statement.encode()).hexdigest(),
                        answer_span=(start, end),
                        answer_quote=statement,
                        answer_quote_sha256=hashlib.sha256(
                            statement.encode()
                        ).hexdigest(),
                        qualifier=candidate.qualifier,
                        scope=candidate.scope,
                        polarity=candidate.polarity,
                        confidence_basis=candidate.confidence_basis,
                        citation_evidence_artifact_ids=candidate.citation_evidence_artifact_ids,
                        source_candidate_ordinal=candidate_ordinal,
                        atomicity_basis=basis,
                    )
                )
        outcome = (
            ClaimNormalizationOutcome.claims_extracted
            if claims
            else ClaimNormalizationOutcome.no_claims
        )
        payload = {
            "schema_version": "bijux.canon.reason.normalized_claim_set.v1",
            "source_synthesis_artifact_id": source_synthesis_artifact_id,
            "answer_text_sha256": hashlib.sha256(answer_text.encode()).hexdigest(),
            "outcome": outcome.value,
            "claims": tuple(claim.model_dump(mode="json") for claim in claims),
        }
        return NormalizedClaimSet(
            artifact_id=content_artifact_id(payload),
            source_synthesis_artifact_id=source_synthesis_artifact_id,
            answer_text_sha256=hashlib.sha256(answer_text.encode()).hexdigest(),
            outcome=outcome,
            claims=tuple(claims),
        )


def _unique_span(answer: str, statement: str) -> int:
    start = answer.find(statement)
    if start < 0:
        raise ClaimNormalizationError(
            ClaimNormalizationErrorCode.answer_span_missing,
            "candidate claim does not occur in the synthesis answer",
        )
    if answer.find(statement, start + 1) >= 0:
        raise ClaimNormalizationError(
            ClaimNormalizationErrorCode.answer_span_ambiguous,
            "candidate claim occurs more than once in the synthesis answer",
        )
    return start


def _atomic_segments(statement: str) -> tuple[tuple[str, int, int, str], ...]:
    spans = []
    cursor = 0
    for match in _BOUNDARY.finditer(statement):
        spans.append((cursor, match.start(), match.group()))
        cursor = match.end()
    spans.append((cursor, len(statement), ""))
    segments = []
    for start, end, delimiter in spans:
        raw = statement[start:end]
        leading = len(raw) - len(raw.lstrip())
        trailing = len(raw) - len(raw.rstrip())
        clean_start = start + leading
        clean_end = end - trailing
        if clean_end <= clean_start:
            continue
        basis = "single_assertion"
        if delimiter.startswith(";"):
            basis = "semicolon_clause"
        elif delimiter:
            basis = "sentence_or_contrast_clause"
        segments.append(
            (statement[clean_start:clean_end], clean_start, clean_end, basis)
        )
    return tuple(segments)


def _is_falsifiable(statement: str) -> bool:
    words = _WORD.findall(statement)
    return len(words) >= 2 and "?" not in statement


def _provider_polarity(value: CandidatePolarity) -> AtomicClaimPolarity:
    return {
        CandidatePolarity.supports: AtomicClaimPolarity.supports,
        CandidatePolarity.opposes: AtomicClaimPolarity.opposes,
        CandidatePolarity.ambiguous: AtomicClaimPolarity.ambiguous,
    }[value]


__all__ = [
    "AtomicClaim",
    "AtomicClaimNormalizer",
    "AtomicClaimPolarity",
    "ClaimConfidenceBasis",
    "ClaimNormalizationError",
    "ClaimNormalizationErrorCode",
    "ClaimNormalizationOutcome",
    "NormalizedClaimSet",
]
