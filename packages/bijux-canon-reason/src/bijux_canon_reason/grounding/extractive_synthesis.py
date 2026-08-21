# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Deterministic credential-free synthesis over bounded evidence packets."""

from __future__ import annotations

from enum import StrEnum
import hashlib
import re
from typing import Literal, Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.fingerprints import fingerprint_obj
from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.evidence_packets import (
    CitationEvidence,
    EvidencePacket,
)

_ARTIFACT_ID = re.compile(r"sha256:[0-9a-f]{64}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_TERM = re.compile(r"[^\W_]+", flags=re.UNICODE)
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+", flags=re.UNICODE)
_CONTRAST = re.compile(r";|,\s+(?:but|whereas|while)\s+", flags=re.IGNORECASE)


def _artifact_id(value: object) -> str:
    return f"sha256:{fingerprint_obj(value)}"


def _require_artifact_id(value: str) -> str:
    if _ARTIFACT_ID.fullmatch(value) is None:
        raise ValueError("artifact identity must be sha256:<64 lowercase hex>")
    return value


def _require_sha256(value: str) -> str:
    if _SHA256.fullmatch(value) is None:
        raise ValueError("content identity must be 64 lowercase hex characters")
    return value


def _terms(text: str) -> frozenset[str]:
    return frozenset(match.group().casefold() for match in _TERM.finditer(text))


class SynthesisStyle(StrEnum):
    """Explicit rhetorical shape selected by the caller's question class."""

    general = "general"
    methods_comparison = "methods_comparison"
    finding_synthesis = "finding_synthesis"
    conflict_preserving = "conflict_preserving"
    limitations_review = "limitations_review"
    multi_hop = "multi_hop"


class SynthesisOutcome(StrEnum):
    """Evidence sufficiency of a credential-free synthesis."""

    answered = "answered"
    partial = "partial"
    insufficient = "insufficient"


class CredentialFreeSynthesisPolicy(StableModel):
    """Deterministic limits and source sufficiency for extractive synthesis."""

    max_points: int = 4
    required_sources: int = 2
    method: str = "credential-free-extractive-v1"

    @field_validator("max_points", "required_sources")
    @classmethod
    def _validate_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("synthesis limits must be positive")
        return value

    @field_validator("method")
    @classmethod
    def _validate_method(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("synthesis method must not be empty")
        return value

    @property
    def artifact_id(self) -> str:
        """Return the content identity of the synthesis policy."""

        return _artifact_id(self.model_dump(mode="json"))


class ExtractiveSynthesisPoint(StableModel):
    """One source-attributed candidate claim with an exact evidence span."""

    artifact_id: str
    statement: str
    statement_sha256: str
    source_id: str
    source_uri: str
    citation_evidence_artifact_id: str
    locator_artifact_id: str
    quote: str
    quote_sha256: str
    evidence_span: tuple[int, int]
    extraction_score: int
    atomicity_basis: str = "single-sentence-or-contrast-clause"

    @field_validator(
        "artifact_id", "citation_evidence_artifact_id", "locator_artifact_id"
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return _require_artifact_id(value)

    @field_validator("statement_sha256", "quote_sha256")
    @classmethod
    def _validate_sha256(cls, value: str) -> str:
        return _require_sha256(value)

    @field_validator("statement", "source_id", "source_uri", "quote")
    @classmethod
    def _validate_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("synthesis point fields must not be empty")
        return value

    @field_validator("evidence_span")
    @classmethod
    def _validate_span(cls, value: tuple[int, int]) -> tuple[int, int]:
        if value[0] < 0 or value[1] <= value[0]:
            raise ValueError("evidence span must be non-empty and ordered")
        return value

    @model_validator(mode="after")
    def _validate_identities(self) -> Self:
        if hashlib.sha256(self.statement.encode()).hexdigest() != self.statement_sha256:
            raise ValueError("statement does not match statement_sha256")
        if hashlib.sha256(self.quote.encode()).hexdigest() != self.quote_sha256:
            raise ValueError("quote does not match quote_sha256")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != _artifact_id(payload):
            raise ValueError("synthesis point identity does not match its payload")
        return self


class CredentialFreeSynthesis(StableModel):
    """Content-addressed offline synthesis with source-scoped candidate claims."""

    schema_version: str = "bijux.canon.reason.credential_free_synthesis.v1"
    artifact_id: str
    question: str
    question_sha256: str
    evidence_packet_artifact_id: str
    synthesis_policy_artifact_id: str
    method: str
    style: SynthesisStyle
    outcome: SynthesisOutcome
    answer_text: str
    answer_text_sha256: str
    points: tuple[ExtractiveSynthesisPoint, ...]
    source_count: int
    limitations: tuple[str, ...]
    provider: None = None
    network_required: Literal[False] = False

    @field_validator(
        "artifact_id", "evidence_packet_artifact_id", "synthesis_policy_artifact_id"
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return _require_artifact_id(value)

    @field_validator("question_sha256", "answer_text_sha256")
    @classmethod
    def _validate_sha256(cls, value: str) -> str:
        return _require_sha256(value)

    @field_validator("question", "answer_text", "method")
    @classmethod
    def _validate_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("synthesis question and answer must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_synthesis(self) -> Self:
        if hashlib.sha256(self.question.encode()).hexdigest() != self.question_sha256:
            raise ValueError("question does not match question_sha256")
        if hashlib.sha256(self.answer_text.encode()).hexdigest() != (
            self.answer_text_sha256
        ):
            raise ValueError("answer does not match answer_text_sha256")
        sources = {point.source_id for point in self.points}
        if self.source_count != len(sources):
            raise ValueError("synthesis source count does not match its points")
        if self.outcome is SynthesisOutcome.insufficient:
            if self.points or self.source_count:
                raise ValueError(
                    "insufficient synthesis cannot expose candidate claims"
                )
        elif not self.points:
            raise ValueError("answered synthesis requires candidate claims")
        if not self.limitations or any(not item.strip() for item in self.limitations):
            raise ValueError("synthesis must state its limitations")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != _artifact_id(payload):
            raise ValueError("synthesis identity does not match its payload")
        return self


class CredentialFreeSynthesizer:
    """Create useful source-attributed synthesis without providers or credentials."""

    def __init__(self, policy: CredentialFreeSynthesisPolicy | None = None) -> None:
        self._policy = policy or CredentialFreeSynthesisPolicy()

    def synthesize(
        self,
        *,
        question: str,
        evidence_packet: EvidencePacket,
        style: SynthesisStyle = SynthesisStyle.general,
    ) -> CredentialFreeSynthesis:
        """Synthesize selected evidence with explicit attribution and limitations."""

        if not question.strip():
            raise ValueError("synthesis question must not be empty")
        selected = evidence_packet.selected[: self._policy.max_points]
        points = tuple(self._point(question, evidence) for evidence in selected)
        source_count = len({point.source_id for point in points})
        if not points:
            outcome = SynthesisOutcome.insufficient
        elif source_count < self._policy.required_sources:
            outcome = SynthesisOutcome.partial
        else:
            outcome = SynthesisOutcome.answered
        limitations = self._limitations(
            style=style,
            outcome=outcome,
            source_count=source_count,
            available_count=len(evidence_packet.selected),
            used_count=len(points),
        )
        answer = self._render(
            style=style,
            outcome=outcome,
            points=points,
            limitations=limitations,
        )
        payload = {
            "schema_version": "bijux.canon.reason.credential_free_synthesis.v1",
            "question": question,
            "question_sha256": hashlib.sha256(question.encode()).hexdigest(),
            "evidence_packet_artifact_id": evidence_packet.artifact_id,
            "synthesis_policy_artifact_id": self._policy.artifact_id,
            "method": self._policy.method,
            "style": style.value,
            "outcome": outcome.value,
            "answer_text": answer,
            "answer_text_sha256": hashlib.sha256(answer.encode()).hexdigest(),
            "points": tuple(point.model_dump(mode="json") for point in points),
            "source_count": source_count,
            "limitations": limitations,
            "provider": None,
            "network_required": False,
        }
        return CredentialFreeSynthesis(
            artifact_id=_artifact_id(payload),
            question=question,
            question_sha256=hashlib.sha256(question.encode()).hexdigest(),
            evidence_packet_artifact_id=evidence_packet.artifact_id,
            synthesis_policy_artifact_id=self._policy.artifact_id,
            method=self._policy.method,
            style=style,
            outcome=outcome,
            answer_text=answer,
            answer_text_sha256=hashlib.sha256(answer.encode()).hexdigest(),
            points=points,
            source_count=source_count,
            limitations=limitations,
        )

    @staticmethod
    def _point(question: str, evidence: CitationEvidence) -> ExtractiveSynthesisPoint:
        quote, start, end, score = _best_clause(question, evidence.exact_text)
        statement = f"{evidence.source_id} reports: “{quote}”"
        payload = {
            "statement": statement,
            "statement_sha256": hashlib.sha256(statement.encode()).hexdigest(),
            "source_id": evidence.source_id,
            "source_uri": evidence.locator.source_uri,
            "citation_evidence_artifact_id": evidence.artifact_id,
            "locator_artifact_id": evidence.locator.artifact_id,
            "quote": quote,
            "quote_sha256": hashlib.sha256(quote.encode()).hexdigest(),
            "evidence_span": (start, end),
            "extraction_score": score,
            "atomicity_basis": "single-sentence-or-contrast-clause",
        }
        return ExtractiveSynthesisPoint(
            artifact_id=_artifact_id(payload),
            statement=statement,
            statement_sha256=hashlib.sha256(statement.encode()).hexdigest(),
            source_id=evidence.source_id,
            source_uri=evidence.locator.source_uri,
            citation_evidence_artifact_id=evidence.artifact_id,
            locator_artifact_id=evidence.locator.artifact_id,
            quote=quote,
            quote_sha256=hashlib.sha256(quote.encode()).hexdigest(),
            evidence_span=(start, end),
            extraction_score=score,
        )

    @staticmethod
    def _limitations(
        *,
        style: SynthesisStyle,
        outcome: SynthesisOutcome,
        source_count: int,
        available_count: int,
        used_count: int,
    ) -> tuple[str, ...]:
        limitations = [
            "This offline extractive synthesis reports source statements; it does not yet establish semantic entailment."
        ]
        if outcome is SynthesisOutcome.insufficient:
            limitations.append(
                "No citation-ready evidence was admitted for this question."
            )
        elif outcome is SynthesisOutcome.partial:
            limitations.append(
                f"Only {source_count} distinct {'source was' if source_count == 1 else 'sources were'} available, so cross-source agreement cannot be established."
            )
        if used_count < available_count:
            limitations.append(
                f"The synthesis used {used_count} of {available_count} admitted citations under its point limit."
            )
        if style is SynthesisStyle.conflict_preserving:
            limitations.append(
                "Potentially divergent accounts remain separate; this pass does not adjudicate conflict."
            )
        elif style is SynthesisStyle.limitations_review:
            limitations.append(
                "Reported limitations remain scoped to each source and are not universal generalizations."
            )
        elif style is SynthesisStyle.methods_comparison:
            limitations.append(
                "Method descriptions are compared by attribution only; methodological equivalence is not assumed."
            )
        elif style is SynthesisStyle.multi_hop:
            limitations.append(
                "The extracted points are not treated as a complete causal or inferential chain."
            )
        return tuple(limitations)

    @staticmethod
    def _render(
        *,
        style: SynthesisStyle,
        outcome: SynthesisOutcome,
        points: tuple[ExtractiveSynthesisPoint, ...],
        limitations: tuple[str, ...],
    ) -> str:
        if outcome is SynthesisOutcome.insufficient:
            return "Insufficient evidence. " + " ".join(limitations)
        heading = {
            SynthesisStyle.general: "The admitted evidence provides source-scoped observations.",
            SynthesisStyle.methods_comparison: "The admitted sources describe methods in distinct study contexts.",
            SynthesisStyle.finding_synthesis: "The admitted sources report findings that can be compared by provenance.",
            SynthesisStyle.conflict_preserving: "The admitted evidence preserves potentially divergent source accounts.",
            SynthesisStyle.limitations_review: "The admitted evidence identifies source-scoped limitations.",
            SynthesisStyle.multi_hop: "The admitted evidence supplies distinct observations for a multi-step question.",
        }[style]
        statements = " ".join(
            f"{point.statement} [citation:{point.citation_evidence_artifact_id}]"
            for point in points
        )
        return f"{heading} {statements} Limits: {' '.join(limitations)}"


def _best_clause(question: str, text: str) -> tuple[str, int, int, int]:
    question_terms = _terms(question)
    candidates: list[tuple[int, int, int, str]] = []
    sentence_spans = []
    cursor = 0
    for boundary in _SENTENCE_BOUNDARY.finditer(text):
        sentence_spans.append((cursor, boundary.start()))
        cursor = boundary.end()
    sentence_spans.append((cursor, len(text)))
    for sentence_start, sentence_end in sentence_spans:
        raw_sentence = text[sentence_start:sentence_end]
        leading = len(raw_sentence) - len(raw_sentence.lstrip())
        trailing = len(raw_sentence) - len(raw_sentence.rstrip())
        start = sentence_start + leading
        end = sentence_end - trailing
        if end <= start:
            continue
        segments = []
        cursor = 0
        for contrast in _CONTRAST.finditer(text[start:end]):
            segments.append((cursor, contrast.start()))
            cursor = contrast.end()
        segments.append((cursor, end - start))
        for left, right in segments:
            clause = text[start + left : start + right]
            clause_leading = len(clause) - len(clause.lstrip(" ;,"))
            clause_trailing = len(clause) - len(clause.rstrip())
            clause_start = start + left + clause_leading
            clause_end = start + right - clause_trailing
            if clause_end <= clause_start:
                continue
            quote = text[clause_start:clause_end]
            overlap = len(question_terms & _terms(quote))
            candidates.append((overlap, clause_start, clause_end, quote))
    if not candidates:
        raise ValueError("citation evidence contains no extractable text")
    score, start, end, quote = min(
        candidates,
        key=lambda item: (-item[0], item[2] - item[1], item[1], item[3]),
    )
    return quote, start, end, score


__all__ = [
    "CredentialFreeSynthesis",
    "CredentialFreeSynthesisPolicy",
    "CredentialFreeSynthesizer",
    "ExtractiveSynthesisPoint",
    "SynthesisOutcome",
    "SynthesisStyle",
]
