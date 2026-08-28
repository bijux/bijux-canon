# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Normalize synthesis candidates into exact-span atomic claims."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
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
    r"(?<=[.!?])\s+|;\s*|,\s+but\s+(?!instead,\s+should\b)|"
    r",\s+(?:although|though|whereas|while)\s+|"
    rf"\s+and\s+(?!(?:[^\W_]+(?:ed|ing))\b)"
    rf"(?=(?:(?:the|this|these|no)\s+)?[^\W_]+\s+{_INDEPENDENT_VERB}\b)",
    flags=re.IGNORECASE,
)
_LEADING_CONCESSION = re.compile(
    r"^\s*(?:although|though|while)\s+(?P<condition>[^,]+),\s*"
    r"(?P<conclusion>.+)$",
    flags=re.IGNORECASE,
)
_WORD = re.compile(r"[^\W_]+", flags=re.UNICODE)
_QUALIFICATION_PREFIX = "bijux.canon.reason.claim-qualification.v1:"
_NEGATION = re.compile(
    r"\b(?:cannot|failed\s+to|neither|never|no|nor|not|without)\b",
    flags=re.IGNORECASE,
)
_RECOMMENDATION = re.compile(
    r"\b(?:ought\s+to|recommend(?:ed|s)?|should)\b", flags=re.IGNORECASE
)
_UNCERTAINTY = re.compile(
    r"\b(?:ambiguous|uncertain|unclear|unknown|remain(?:s|ed)?\s+to\s+be\s+"
    r"determined)\b",
    flags=re.IGNORECASE,
)
_POSSIBILITY = re.compile(
    r"\b(?:can|could|may|might|possible|potentially)\b", flags=re.IGNORECASE
)
_PROBABILITY = re.compile(
    r"\b(?:likely|probably|suggest(?:s|ed)?)\b", flags=re.IGNORECASE
)
_OPINION = re.compile(
    r"^\s*(?:in\s+(?:my|our)\s+opinion\s*,?|(?:i|we)\s+"
    r"(?:believe|feel|guess|think)\b)",
    flags=re.IGNORECASE,
)
_TRANSITION_ONLY = re.compile(
    r"^\s*(?:however|in\s+addition|moreover|nevertheless|therefore|thus)"
    r"[.!]?\s*$",
    flags=re.IGNORECASE,
)
_QUANTITATIVE_SCOPE = re.compile(
    r"\b(?:(?:approximately|at\s+least|below|fewer\s+than|higher\s+than|"
    r"less\s+than|lower\s+than|more\s+than|over|up\s+to|~)\s+)?"
    r"\d[\d,.]*(?:[–-]\d[\d,.]*)?\s*(?:%|[–-]?fold|times?)?"
    r"(?![\w%–-])",
    flags=re.IGNORECASE,
)
_TEMPORAL_SCOPE = re.compile(
    r"\b(?:for\s+many\s+years|decades-old|(?:between\s+)?"
    r"(?:\d[\d,]*(?:[–-]\d[\d,]*)?\s*(?:calibrated\s+)?"
    r"(?:years?\s+before\s+present|years?|[–-]?year-old|cal\.?\s*BP|BP|BCE|CE)"
    r"|[a-z]+-year-old))\b",
    flags=re.IGNORECASE,
)
_POPULATION_SCOPE = re.compile(
    r"\b(?:at\s+least\s+one\s+of\s+the\s+\w+|"
    r"(?:(?:ancient|archaeological|common|ethanol-preserved|fossil|"
    r"garter-snake|historical|hot|human|mammalian|museum|permafrost-preserved|"
    r"resin-embedded|soft|tested)\s+){0,4}"
    r"(?:individuals?|organisms?|populations?|samples?|specimens?|tissues?)"
    r"(?:\s+from\s+(?:(?!(?:are|is|that|was|were|which|who)\b)"
    r"[\w()-]+\s*){1,6})?)\b",
    flags=re.IGNORECASE,
)


class AtomicClaimPolarity(StrEnum):
    """Normalized candidate polarity before entailment verification."""

    supports = "supports"
    opposes = "opposes"
    ambiguous = "ambiguous"
    observed = "observed"


class ClaimConfidenceBasis(StrEnum):
    """Why an unverified normalized claim has its candidate status."""

    exact_extractive_span = "exact_extractive_span"
    conservative_evidence_projection = "conservative_evidence_projection"
    structured_provider_candidate = "structured_provider_candidate"


class ClaimContentKind(StrEnum):
    """Semantic kind admitted to, or excluded from, factual claim metrics."""

    factual_assertion = "factual_assertion"
    recommendation = "recommendation"
    opinion = "opinion"
    question = "question"
    transition = "transition"


class ClaimModality(StrEnum):
    """The strongest explicit modality retained from an atomic statement."""

    asserted = "asserted"
    possible = "possible"
    probable = "probable"
    recommended = "recommended"
    uncertain = "uncertain"


class AtomicClaimQualification(StableModel):
    """Conservative lexical qualifications retained with an atomic claim."""

    schema_version: str = "bijux.canon.reason.claim_qualification.v1"
    content_kind: ClaimContentKind
    modality: ClaimModality
    negated: bool
    population_scope: tuple[str, ...]
    temporal_scope: tuple[str, ...]
    quantitative_scope: tuple[str, ...]
    source_qualifier: str | None


class ClaimNormalizationOutcome(StrEnum):
    """Whether normalized claims exist for a synthesis."""

    claims_extracted = "claims_extracted"
    no_claims = "no_claims"


class ClaimNormalizationErrorCode(StrEnum):
    """Stable fail-closed claim normalization errors."""

    answer_span_missing = "answer_span_missing"
    answer_span_ambiguous = "answer_span_ambiguous"
    candidate_not_falsifiable = "candidate_not_falsifiable"
    candidate_not_factual = "candidate_not_factual"


class ClaimNormalizationError(ValueError):
    """A synthesis claim cannot be bound to an exact answer span."""

    def __init__(
        self,
        code: ClaimNormalizationErrorCode,
        message: str,
        *,
        content_kind: ClaimContentKind | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.content_kind = content_kind


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

    @property
    def qualification(self) -> AtomicClaimQualification:
        """Decode typed qualification while retaining historical artifacts."""

        return _decode_qualification(self.qualifier, self.statement)

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
    source_atomicity_basis: str


@dataclass(frozen=True, slots=True)
class _PreparedClaim:
    statement: str
    start: int
    end: int
    segment_basis: str
    source_candidate_ordinal: int
    candidate: _ClaimInput
    content_kind: ClaimContentKind


class AtomicClaimNormalizer:
    """Split, bind, and preserve every candidate assertion without collapsing it."""

    def normalize_credential_free(
        self, synthesis: CredentialFreeSynthesis
    ) -> NormalizedClaimSet:
        """Normalize deterministic extractive points into exact-span claims."""

        inputs = tuple(
            _ClaimInput(
                statement=point.statement,
                qualifier=None,
                scope=point.source_id,
                polarity=AtomicClaimPolarity.observed,
                confidence_basis=(
                    ClaimConfidenceBasis.conservative_evidence_projection
                    if point.atomicity_basis.startswith("conservative-projection:")
                    else ClaimConfidenceBasis.exact_extractive_span
                ),
                citation_evidence_artifact_ids=(point.citation_evidence_artifact_id,),
                source_atomicity_basis=point.atomicity_basis,
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
                source_atomicity_basis="structured-provider-candidate",
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
        prepared: list[_PreparedClaim] = []
        for candidate_ordinal, candidate in enumerate(candidates, start=1):
            candidate_start = _unique_span(answer_text, candidate.statement)
            for statement, relative_start, relative_end, basis in _atomic_segments(
                candidate.statement
            ):
                content_kind = _content_kind(statement)
                if content_kind in {
                    ClaimContentKind.opinion,
                    ClaimContentKind.transition,
                }:
                    raise ClaimNormalizationError(
                        ClaimNormalizationErrorCode.candidate_not_factual,
                        f"{content_kind.value} candidate cannot enter factual metrics",
                        content_kind=content_kind,
                    )
                if content_kind is ClaimContentKind.question or not _is_falsifiable(
                    statement
                ):
                    raise ClaimNormalizationError(
                        ClaimNormalizationErrorCode.candidate_not_falsifiable,
                        "candidate claim is not a falsifiable assertion",
                    )
                start = candidate_start + relative_start
                end = candidate_start + relative_end
                assert answer_text[start:end] == statement
                prepared.append(
                    _PreparedClaim(
                        statement=statement,
                        start=start,
                        end=end,
                        segment_basis=basis,
                        source_candidate_ordinal=candidate_ordinal,
                        candidate=candidate,
                        content_kind=content_kind,
                    )
                )
        claims: list[AtomicClaim] = []
        for ordinal, item in enumerate(
            sorted(prepared, key=lambda claim: (claim.start, claim.end)), start=1
        ):
            statement = item.statement
            candidate = item.candidate
            qualification = _qualification(
                statement,
                content_kind=item.content_kind,
                source_qualifier=candidate.qualifier,
            )
            encoded_qualification = _encode_qualification(qualification)
            atomicity_basis = f"{candidate.source_atomicity_basis}|{item.segment_basis}"
            payload = {
                "ordinal": ordinal,
                "statement": statement,
                "statement_sha256": hashlib.sha256(statement.encode()).hexdigest(),
                "answer_span": (item.start, item.end),
                "answer_quote": statement,
                "answer_quote_sha256": hashlib.sha256(statement.encode()).hexdigest(),
                "qualifier": encoded_qualification,
                "scope": candidate.scope,
                "polarity": candidate.polarity.value,
                "confidence_basis": candidate.confidence_basis.value,
                "citation_evidence_artifact_ids": candidate.citation_evidence_artifact_ids,
                "source_candidate_ordinal": item.source_candidate_ordinal,
                "atomicity_basis": atomicity_basis,
            }
            claims.append(
                AtomicClaim(
                    artifact_id=content_artifact_id(payload),
                    ordinal=ordinal,
                    statement=statement,
                    statement_sha256=hashlib.sha256(statement.encode()).hexdigest(),
                    answer_span=(item.start, item.end),
                    answer_quote=statement,
                    answer_quote_sha256=hashlib.sha256(statement.encode()).hexdigest(),
                    qualifier=encoded_qualification,
                    scope=candidate.scope,
                    polarity=candidate.polarity,
                    confidence_basis=candidate.confidence_basis,
                    citation_evidence_artifact_ids=candidate.citation_evidence_artifact_ids,
                    source_candidate_ordinal=item.source_candidate_ordinal,
                    atomicity_basis=atomicity_basis,
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
    concession = _LEADING_CONCESSION.match(statement)
    if concession is not None:
        result = []
        for group_name in ("condition", "conclusion"):
            group_start = concession.start(group_name)
            group_text = concession.group(group_name)
            for text, start, end, basis in _regular_atomic_segments(group_text):
                result.append(
                    (
                        text,
                        group_start + start,
                        group_start + end,
                        f"leading_concession_clause:{basis}",
                    )
                )
        return tuple(result)
    return _regular_atomic_segments(statement)


def _regular_atomic_segments(
    statement: str,
) -> tuple[tuple[str, int, int, str], ...]:
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


def _content_kind(statement: str) -> ClaimContentKind:
    if "?" in statement:
        return ClaimContentKind.question
    if _TRANSITION_ONLY.fullmatch(statement):
        return ClaimContentKind.transition
    if _OPINION.match(statement):
        return ClaimContentKind.opinion
    if _RECOMMENDATION.search(statement):
        return ClaimContentKind.recommendation
    return ClaimContentKind.factual_assertion


def _qualification(
    statement: str,
    *,
    content_kind: ClaimContentKind,
    source_qualifier: str | None,
) -> AtomicClaimQualification:
    modality = ClaimModality.asserted
    if _RECOMMENDATION.search(statement):
        modality = ClaimModality.recommended
    elif _UNCERTAINTY.search(statement):
        modality = ClaimModality.uncertain
    elif _POSSIBILITY.search(statement):
        modality = ClaimModality.possible
    elif _PROBABILITY.search(statement):
        modality = ClaimModality.probable
    return AtomicClaimQualification(
        content_kind=content_kind,
        modality=modality,
        negated=bool(_NEGATION.search(statement)),
        population_scope=_matches(_POPULATION_SCOPE, statement),
        temporal_scope=_matches(_TEMPORAL_SCOPE, statement),
        quantitative_scope=_matches(_QUANTITATIVE_SCOPE, statement),
        source_qualifier=source_qualifier,
    )


def _matches(pattern: re.Pattern[str], statement: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(match.group().strip() for match in pattern.finditer(statement))
    )


def _encode_qualification(qualification: AtomicClaimQualification) -> str:
    encoded = json.dumps(
        qualification.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"{_QUALIFICATION_PREFIX}{encoded}"


def _decode_qualification(
    encoded: str | None, statement: str
) -> AtomicClaimQualification:
    if encoded and encoded.startswith(_QUALIFICATION_PREFIX):
        return AtomicClaimQualification.model_validate_json(
            encoded.removeprefix(_QUALIFICATION_PREFIX)
        )
    return _qualification(
        statement,
        content_kind=_content_kind(statement),
        source_qualifier=encoded,
    )


def _provider_polarity(value: CandidatePolarity) -> AtomicClaimPolarity:
    return {
        CandidatePolarity.supports: AtomicClaimPolarity.supports,
        CandidatePolarity.opposes: AtomicClaimPolarity.opposes,
        CandidatePolarity.ambiguous: AtomicClaimPolarity.ambiguous,
    }[value]


__all__ = [
    "AtomicClaim",
    "AtomicClaimQualification",
    "AtomicClaimNormalizer",
    "AtomicClaimPolarity",
    "ClaimConfidenceBasis",
    "ClaimContentKind",
    "ClaimModality",
    "ClaimNormalizationError",
    "ClaimNormalizationErrorCode",
    "ClaimNormalizationOutcome",
    "NormalizedClaimSet",
]
