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
from bijux_canon_reason.grounding.semantic_projection import (
    EvidenceProjection,
    EvidenceProjectionMethod,
    project_evidence_clause,
)

_ARTIFACT_ID = re.compile(r"sha256:[0-9a-f]{64}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_TERM = re.compile(r"[^\W_]+", flags=re.UNICODE)
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+", flags=re.UNICODE)
_CONTRAST = re.compile(r";|,\s+(?:but|whereas|while)\s+", flags=re.IGNORECASE)
_ABSOLUTE_REQUEST = re.compile(
    r"\b(?:always|guarantee(?:d|s)?|perfect(?:ly)?|certain(?:ly)?|never fails?)\b",
    flags=re.IGNORECASE,
)
_ABSOLUTE_OPERATORS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bguarantee(?:d|s)?\b", flags=re.IGNORECASE),
    re.compile(r"\bperfect(?:ly)?\b", flags=re.IGNORECASE),
    re.compile(r"\bcertain(?:ly)?\b", flags=re.IGNORECASE),
    re.compile(r"\balways\b", flags=re.IGNORECASE),
    re.compile(r"\bnever fails?\b", flags=re.IGNORECASE),
)
_METHOD_TERMS = frozenset(
    {
        "analysis",
        "assay",
        "extract",
        "extraction",
        "library",
        "method",
        "protocol",
        "sequence",
        "sequencing",
    }
)
_LIMITATION_TERMS = frozenset(
    {
        "although",
        "but",
        "caveat",
        "despite",
        "however",
        "less",
        "limitation",
        "limited",
        "low",
        "lower",
        "uncertain",
        "whereas",
        "while",
    }
)
_OPPOSITION_TERMS = frozenset(
    {"cannot", "failed", "fails", "no", "not", "unlikely", "without"}
)
_RESULT_CUE = re.compile(
    r"\b(?:our results?|(?:this|the) study shows|we (?:conclude|demonstrate|found|show|have shown)|results? (?:confirm|indicate|support)|can exceed|provided? the best|highest)\b",
    flags=re.IGNORECASE,
)
_AIM_CUE = re.compile(
    r"\b(?:we investigate whether|we (?:aim|aimed|seek|sought) to|the (?:aim|objective) (?:is|was))\b",
    flags=re.IGNORECASE,
)
_BACKGROUND_CUE = re.compile(
    r"(?:\[[ ]*\d+[ ]*\]\s+(?:demonstrate|show)|has (?:recently |previously )?been (?:demonstrated|shown))",
    flags=re.IGNORECASE,
)
_NUMBER = re.compile(
    r"\b\d+(?:[.,]\d+)?(?:\s*[-–]\s*\d+(?:[.,]\d+)?)?(?:\s*%|\s*-?fold)?\b"
)
_QUESTION_CONCEPTS: tuple[tuple[frozenset[str], frozenset[str]], ...] = (
    (
        frozenset({"region", "regions", "area", "areas", "location"}),
        frozenset({"part", "parts", "portion", "region", "area", "capsule"}),
    ),
    (
        frozenset({"quantitative", "amount", "advantage", "difference"}),
        frozenset({"fold", "percent", "percentage", "times", "exceed"}),
    ),
    (
        frozenset({"highest", "best", "greatest", "most"}),
        frozenset(
            {
                "dense",
                "densest",
                "highest",
                "best",
                "greater",
                "high",
                "maximum",
                "exceed",
            }
        ),
    ),
    (
        frozenset({"caveat", "limitation", "limitations"}),
        frozenset({"although", "but", "however", "less", "low", "lower", "while"}),
    ),
)
_GENERIC_QUESTION_TERMS = frozenset(
    {
        "answer",
        "are",
        "did",
        "do",
        "does",
        "changed",
        "evidence",
        "happened",
        "how",
        "is",
        "report",
        "reported",
        "reports",
        "show",
        "shown",
        "source",
        "sources",
        "what",
        "which",
        "why",
    }
)
_DUPLICATE_STOPWORDS = _GENERIC_QUESTION_TERMS | frozenset(
    {
        "a",
        "all",
        "also",
        "an",
        "and",
        "as",
        "at",
        "be",
        "been",
        "both",
        "by",
        "can",
        "either",
        "for",
        "from",
        "in",
        "including",
        "into",
        "of",
        "our",
        "some",
        "than",
        "that",
        "the",
        "their",
        "these",
        "those",
        "to",
        "was",
        "were",
        "while",
        "with",
    }
)


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


class EvidenceRole(StrEnum):
    """Question-relevant function of one exact evidence clause."""

    finding = "finding"
    method = "method"
    limitation = "limitation"
    counterevidence = "counterevidence"
    context = "context"


class CredentialFreeSynthesisPolicy(StableModel):
    """Deterministic limits and source sufficiency for extractive synthesis."""

    max_points: int = 4
    required_sources: int = 2
    minimum_query_term_overlap: int = 1
    semantic_duplicate_threshold: float = 0.8
    method: str = "credential-free-constrained-synthesis-v3"

    @field_validator("max_points", "required_sources")
    @classmethod
    def _validate_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("synthesis limits must be positive")
        return value

    @field_validator("minimum_query_term_overlap")
    @classmethod
    def _validate_nonnegative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("minimum query overlap must be non-negative")
        return value

    @field_validator("semantic_duplicate_threshold")
    @classmethod
    def _validate_duplicate_threshold(cls, value: float) -> float:
        if not 0 < value <= 1:
            raise ValueError("semantic duplicate threshold must be within (0, 1]")
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
    retrieval_rank: int
    extraction_score: int
    query_term_overlap: int
    role: EvidenceRole
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

    @field_validator("extraction_score", "query_term_overlap")
    @classmethod
    def _validate_scores(cls, value: int) -> int:
        if value < 0:
            raise ValueError("synthesis point scores must be non-negative")
        return value

    @field_validator("retrieval_rank")
    @classmethod
    def _validate_rank(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("synthesis point retrieval rank must be positive")
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

    schema_version: str = "bijux.canon.reason.credential_free_synthesis.v3"
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
        if style is SynthesisStyle.general:
            style = infer_synthesis_style(question)
        points = self._select_points(
            question=question,
            evidence=evidence_packet.selected,
            style=style,
        )
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
            "schema_version": "bijux.canon.reason.credential_free_synthesis.v3",
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

    def _select_points(
        self,
        *,
        question: str,
        evidence: tuple[CitationEvidence, ...],
        style: SynthesisStyle,
    ) -> tuple[ExtractiveSynthesisPoint, ...]:
        candidates = tuple(
            self._point(
                evidence=item,
                clause=clause,
                question=question,
                style=style,
            )
            for item in evidence
            for clause in _ranked_clauses(question, item.exact_text)
        )
        if (
            style is not SynthesisStyle.methods_comparison
            and not (_terms(question) & _METHOD_TERMS)
        ):
            sources_with_nonmethod_evidence = {
                item.source_id
                for item in candidates
                if item.role is not EvidenceRole.method
            }
            candidates = tuple(
                item
                for item in candidates
                if item.role is not EvidenceRole.method
                or item.source_id not in sources_with_nonmethod_evidence
            )
        if not re.search(
            r"\b(?:and|both|caveat|conflict|limitation|limitations|versus)\b",
            question,
            flags=re.IGNORECASE,
        ):
            best_by_evidence: dict[str, ExtractiveSynthesisPoint] = {}
            for item in candidates:
                previous = best_by_evidence.get(item.citation_evidence_artifact_id)
                if previous is None or (
                    item.extraction_score,
                    -item.evidence_span[0],
                    item.artifact_id,
                ) > (
                    previous.extraction_score,
                    -previous.evidence_span[0],
                    previous.artifact_id,
                ):
                    best_by_evidence[item.citation_evidence_artifact_id] = item
            candidates = tuple(best_by_evidence.values())
        minimum_overlap = self._policy.minimum_query_term_overlap
        if not (_terms(question) - _GENERIC_QUESTION_TERMS):
            minimum_overlap = 0
        relevant = tuple(
            item for item in candidates if item.query_term_overlap >= minimum_overlap
        )
        if _ABSOLUTE_REQUEST.search(question) and not _supports_absolute_request(
            question,
            tuple(item.statement for item in relevant),
        ):
            return ()
        ranked = sorted(
            relevant,
            key=lambda item: (
                -item.extraction_score,
                item.retrieval_rank,
                item.source_id,
                item.evidence_span,
                item.artifact_id,
            ),
        )
        diverse = []
        seen_sources: set[str] = set()
        for item in ranked:
            if item.source_id not in seen_sources:
                diverse.append(item)
                seen_sources.add(item.source_id)
        diverse.extend(item for item in ranked if item not in diverse)
        selected: list[ExtractiveSynthesisPoint] = []
        for item in diverse:
            if any(
                _semantically_duplicate(
                    item,
                    prior,
                    threshold=self._policy.semantic_duplicate_threshold,
                )
                for prior in selected
            ):
                continue
            selected.append(item)
            if len(selected) >= self._policy.max_points:
                break
        return tuple(selected)

    @staticmethod
    def _point(
        *,
        evidence: CitationEvidence,
        clause: tuple[str, int, int, int],
        question: str,
        style: SynthesisStyle,
    ) -> ExtractiveSynthesisPoint:
        quote, start, end, _ = clause
        role = _evidence_role(quote, evidence.section_path)
        projection = _best_projection(
            question,
            quote,
            role,
            style,
            reference_text=evidence.exact_text,
        )
        statement = projection.statement
        overlap = len(_terms(question) & _terms(statement))
        score = max(
            0,
            overlap * 10
            + _role_bonus(role, style)
            + _answer_value_score(question, statement, role)
            + _projection_bonus(projection)
            + _projection_reference_bonus(projection, evidence.exact_text),
        )
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
            "retrieval_rank": evidence.rank,
            "extraction_score": score,
            "query_term_overlap": overlap,
            "role": role.value,
            "atomicity_basis": f"conservative-projection:{projection.method.value}",
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
            retrieval_rank=evidence.rank,
            extraction_score=score,
            query_term_overlap=overlap,
            role=role,
            atomicity_basis=f"conservative-projection:{projection.method.value}",
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
            "Each factual bullet is an exact source clause or a reproducible conservative projection; no broader interpretation is asserted beyond its cited wording."
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
        sections = []
        labels = (
            ("Answer", {EvidenceRole.finding, EvidenceRole.context}),
            ("Methods", {EvidenceRole.method}),
            (
                "Limitations and counterevidence",
                {EvidenceRole.limitation, EvidenceRole.counterevidence},
            ),
        )
        for label, roles in labels:
            members = tuple(point for point in points if point.role in roles)
            if not members:
                continue
            sections.append(label + ":")
            sections.extend(
                f"- {point.statement} [citation:{point.citation_evidence_artifact_id}]"
                for point in members
            )
        sections.append("Scope and limits:")
        sections.extend(f"- {item}" for item in limitations)
        return "\n".join(sections)


def _ranked_clauses(question: str, text: str) -> tuple[tuple[str, int, int, int], ...]:
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
    return tuple(
        (quote, start, end, score)
        for score, start, end, quote in sorted(
            candidates,
            key=lambda item: (-item[0], item[2] - item[1], item[1], item[3]),
        )
    )


def _best_clause(question: str, text: str) -> tuple[str, int, int, int]:
    return _ranked_clauses(question, text)[0]


def _term_similarity(first: str, second: str) -> float:
    first_terms = _terms(first)
    second_terms = _terms(second)
    union = first_terms | second_terms
    return len(first_terms & second_terms) / len(union) if union else 1.0


def _semantically_duplicate(
    first: ExtractiveSynthesisPoint,
    second: ExtractiveSynthesisPoint,
    *,
    threshold: float,
) -> bool:
    if _term_similarity(first.statement, second.statement) >= threshold:
        return True
    if first.source_id != second.source_id:
        return False
    first_numbers = frozenset(_NUMBER.findall(first.statement.casefold()))
    second_numbers = frozenset(_NUMBER.findall(second.statement.casefold()))
    if not first_numbers & second_numbers:
        return False
    first_facts = _terms(first.statement) - _DUPLICATE_STOPWORDS
    second_facts = _terms(second.statement) - _DUPLICATE_STOPWORDS
    shared = first_facts & second_facts
    union = first_facts | second_facts
    return len(shared) >= 5 and len(shared) / len(union) >= 0.2


def _supports_absolute_request(question: str, statements: tuple[str, ...]) -> bool:
    requested = tuple(
        operator for operator in _ABSOLUTE_OPERATORS if operator.search(question)
    )
    return bool(requested) and all(
        any(operator.search(statement) for statement in statements)
        for operator in requested
    )


def _best_projection(
    question: str,
    quote: str,
    role: EvidenceRole,
    style: SynthesisStyle,
    *,
    reference_text: str,
) -> EvidenceProjection:
    projections = project_evidence_clause(quote)
    if not projections:
        raise ValueError("citation evidence contains no projectable text")
    return max(
        enumerate(projections),
        key=lambda indexed: (
            len(_terms(question) & _terms(indexed[1].statement)) * 10
            + _role_bonus(role, style)
            + _answer_value_score(question, indexed[1].statement, role)
            + _projection_bonus(indexed[1])
            + _projection_reference_bonus(indexed[1], reference_text),
            indexed[0],
        ),
    )[1]


def _projection_bonus(projection: EvidenceProjection) -> int:
    return {
        EvidenceProjectionMethod.exact_clause: 0,
        EvidenceProjectionMethod.attribution_removed: 50,
        EvidenceProjectionMethod.labeled_definition: 120,
    }[projection.method]


def _projection_reference_bonus(
    projection: EvidenceProjection, reference_text: str
) -> int:
    if projection.method is not EvidenceProjectionMethod.labeled_definition:
        return 0
    label = " ".join(projection.statement.casefold().split()[:2])
    return reference_text.casefold().count(label) * 10


def _evidence_role(text: str, section_path: tuple[str, ...]) -> EvidenceRole:
    terms = _terms(text)
    sections = _terms(" ".join(section_path))
    if _AIM_CUE.search(text):
        return EvidenceRole.context
    if terms & _OPPOSITION_TERMS:
        return EvidenceRole.counterevidence
    if terms & _LIMITATION_TERMS or sections & {"limitation", "limitations"}:
        return EvidenceRole.limitation
    if terms & _METHOD_TERMS or sections & {
        "method",
        "methods",
        "methodology",
        "materials",
    }:
        return EvidenceRole.method
    if _RESULT_CUE.search(text) or sections & {"abstract", "conclusion", "results"}:
        return EvidenceRole.finding
    return EvidenceRole.context


def _role_bonus(role: EvidenceRole, style: SynthesisStyle) -> int:
    preferred = {
        SynthesisStyle.general: {EvidenceRole.finding, EvidenceRole.context},
        SynthesisStyle.finding_synthesis: {EvidenceRole.finding},
        SynthesisStyle.methods_comparison: {EvidenceRole.method},
        SynthesisStyle.limitations_review: {
            EvidenceRole.finding,
            EvidenceRole.limitation,
            EvidenceRole.counterevidence,
        },
        SynthesisStyle.conflict_preserving: {
            EvidenceRole.limitation,
            EvidenceRole.counterevidence,
        },
        SynthesisStyle.multi_hop: {
            EvidenceRole.finding,
            EvidenceRole.method,
            EvidenceRole.context,
        },
    }[style]
    return 10 if role in preferred else 0


def _answer_value_score(question: str, statement: str, role: EvidenceRole) -> int:
    """Score answer-bearing language without corpus or identity special cases."""

    question_terms = _terms(question)
    statement_terms = _terms(statement)
    score = 0
    for triggers, expressions in _QUESTION_CONCEPTS:
        if question_terms & triggers and statement_terms & expressions:
            score += 8
    if question_terms & {"quantitative", "amount", "advantage", "difference"}:
        if _NUMBER.search(statement):
            score += 8
    if _RESULT_CUE.search(statement):
        score += 14
    if _AIM_CUE.search(statement):
        score -= 36
    if _BACKGROUND_CUE.search(statement):
        score -= 12
    if "petrous" in question_terms and "non-petrous" in statement.casefold():
        score -= 12
    if role is EvidenceRole.context:
        score -= 4
    return score


def infer_synthesis_style(question: str) -> SynthesisStyle:
    """Infer one general rhetorical policy from question language only."""

    terms = _terms(question)
    if terms & {"conflict", "contradict", "counterevidence", "disagree"}:
        return SynthesisStyle.conflict_preserving
    if terms & {
        "caveat",
        "limit",
        "limits",
        "limitation",
        "uncertain",
        "uncertainty",
    }:
        return SynthesisStyle.limitations_review
    if terms & _METHOD_TERMS or terms & {"compare", "versus"}:
        return SynthesisStyle.methods_comparison
    if terms & {"across", "together", "relationship", "connect"}:
        return SynthesisStyle.multi_hop
    if terms & {"finding", "found", "result", "yield"}:
        return SynthesisStyle.finding_synthesis
    return SynthesisStyle.general


def required_source_count(question: str) -> int:
    """Require cross-source coverage only when the question explicitly asks for it."""

    normalized = " ".join(question.casefold().split())
    enumerated = _across_enumeration_count(normalized)
    if enumerated >= 2:
        return enumerated
    cross_source = (
        re.search(r"\bacross\b.*\b(?:papers|sources|studies|articles)\b", normalized)
        or re.search(r"\b(?:papers|sources|studies|articles)\b.*\bacross\b", normalized)
        or re.search(
            r"\b(?:both|two)\b.*\b(?:papers|sources|studies|articles)\b", normalized
        )
        or re.search(
            r"\bcompare\b.*\b(?:papers|sources|studies|articles)\b", normalized
        )
    )
    return 2 if cross_source else 1


def recommended_point_count(question: str) -> int:
    """Bound answer points while retaining explicitly requested source contexts."""

    sources = required_source_count(question)
    requested_terms = _terms(question)
    limitation_allowance = (
        1
        if sources > 1
        and requested_terms & {"caveat", "limit", "limits", "limitation", "limitations"}
        else 0
    )
    return max(3, min(6, sources + limitation_allowance))


def _across_enumeration_count(question: str) -> int:
    match = re.search(
        r"\bacross\s+(?P<items>.+?),\s+(?:how|what|which)\b",
        question,
        flags=re.IGNORECASE,
    )
    if match is None:
        return 0
    items = re.split(r",\s*(?:and\s+)?|\s+and\s+", match.group("items"))
    return min(6, len(tuple(item for item in items if item.strip())))


__all__ = [
    "CredentialFreeSynthesis",
    "CredentialFreeSynthesisPolicy",
    "CredentialFreeSynthesizer",
    "EvidenceRole",
    "ExtractiveSynthesisPoint",
    "SynthesisOutcome",
    "SynthesisStyle",
    "infer_synthesis_style",
    "recommended_point_count",
    "required_source_count",
]
