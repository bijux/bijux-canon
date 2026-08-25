# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Deterministic credential-free synthesis over bounded evidence packets."""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
import hashlib
import math
import re
from typing import Literal, Protocol, Self

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
_NONTERMINAL_ABBREVIATION = re.compile(
    r"\b(?:al|cf|e\.g|figs?|i\.e|nos?|pp?|secs?|vols?|vs)\.$",
    flags=re.IGNORECASE,
)
_CONTRAST = re.compile(
    r";|,\s+but\s+(?!instead,\s+should\b)|,\s+(?:whereas|while)\s+",
    flags=re.IGNORECASE,
)
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
    r"\b(?:our results?|(?:this|the) study shows|these (?:results|specimens)|"
    r"we (?:conclude|demonstrate|found|observed|show|were unable|have shown)|"
    r"results? (?:confirm|indicate|support)|can exceed|provided? the best|highest|"
    r"oldest .{0,32} sequenced)\b",
    flags=re.IGNORECASE,
)
_AIM_CUE = re.compile(
    r"\b(?:we investigate whether|we (?:aim|aimed|seek|sought) to|the (?:aim|objective) (?:is|was))\b",
    flags=re.IGNORECASE,
)
_BACKGROUND_CUE = re.compile(
    r"(?:\[[ ]*\d+[ ]*\]\s+(?:demonstrate|show)|"
    r"has (?:recently |previously )?been (?:demonstrated|shown)|"
    r"(?:conference|opinion piece)\b|first major study|^for context\b|"
    r"^the recent .{0,80}\bdemonstrated\b)",
    flags=re.IGNORECASE,
)
_SETUP_CUE = re.compile(
    r"\b(?:to address (?:this|these) (?:issue|issues)|"
    r"(?:comparative )?(?:analysis|experiment|study) was designed to|"
    r"(?:we|this study) (?:investigate|investigated) whether|"
    r"(?:an?\s+)?(?:original )?goal(?: of (?:this|the) study)? (?:is|was)|"
    r"raises? the question (?:of|whether)|"
    r"no standardized protocol has emerged)\b",
    flags=re.IGNORECASE,
)
_DECISIVE_CUE = re.compile(
    r"\b(?:cannot|could not|did not|failed to|indistinguishable|"
    r"in no instance|need not|not (?:necessary|reliable|sufficient)|"
    r"recommend(?:ed|s)?|should|solely|alone)\b",
    flags=re.IGNORECASE,
)
_RECOMMENDATION_CUE = re.compile(
    r"\b(?:case-by-case|need not|ought to|recommend(?:ed|s)?|should)\b",
    flags=re.IGNORECASE,
)
_COMPARISON_CUE = re.compile(
    r"\b(?:agree(?:d|ment)?|compar(?:e|ed|ing)|differ(?:ed|ence)?|identical|"
    r"same|versus|relative to|higher|lower|exceed(?:ed|s)?)\b",
    flags=re.IGNORECASE,
)
_METHOD_CUE = re.compile(
    r"\b(?:analys(?:e|ed|is)|assay(?:ed)?|clon(?:e|ed|ing)|"
    r"extract(?:ed|ion)?|libraries|library|protocol|replicat(?:e|ed|ion)|"
    r"sequenc(?:e|ed|ing)|test(?:ed)?)\b",
    flags=re.IGNORECASE,
)
_NUMBER = re.compile(
    r"\b\d+(?:[.,]\d+)?(?:\s*[-–]\s*\d+(?:[.,]\d+)?)?(?:\s*%|\s*-?fold)?\b"
)
_ADVANTAGE_CUE = re.compile(
    r"\b(?:exceed(?:ed|s)?|greater|higher|\d+(?:[.,]\d+)?\s*-?fold|times)\b",
    flags=re.IGNORECASE,
)
_SUPERLATIVE_RESULT_CUE = re.compile(
    r"\b(?:best|densest|greatest|highest|maximum|optimal)\b",
    flags=re.IGNORECASE,
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
    (
        frozenset({"authenticate", "authenticating", "authentication"}),
        frozenset(
            {
                "authentic",
                "authenticity",
                "authenticate",
                "authentication",
                "distinguish",
                "distinguished",
                "evidence",
            }
        ),
    ),
    (
        frozenset({"replication", "replications", "replicate", "replicates"}),
        frozenset({"independent", "platform", "platforms", "replicate", "replicates"}),
    ),
    (
        frozenset({"signal", "signals"}),
        frozenset({"evidence", "hallmark", "hallmarks", "junction", "junctions", "specificity"}),
    ),
    (
        frozenset({"specimen", "specimens", "material", "materials"}),
        frozenset({"material", "materials", "sample", "samples", "source", "sources", "specimen", "specimens"}),
    ),
    (
        frozenset({"history", "preservation", "preserved"}),
        frozenset({"age", "aged", "date", "dated", "preserved", "stored", "years"}),
    ),
    (
        frozenset({"analysis", "analyses", "possible"}),
        frozenset({"analysis", "analyses", "feasible", "genomic", "metagenomic", "profile", "profiles"}),
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


class SemanticEmbeddingBatch(Protocol):
    """Embedding result required by credential-free semantic ranking."""

    @property
    def vectors(self) -> tuple[tuple[float, ...], ...]:
        """Return vectors in request order."""
        ...

    @property
    def model_lock_id(self) -> str:
        """Return the immutable model identity used for the batch."""
        ...


class SemanticEmbeddingService(Protocol):
    """Locked local embedding behavior without an Index package dependency."""

    @property
    def model_lock_id(self) -> str:
        """Return the immutable local model identity."""
        ...

    def embed(self, texts: Sequence[str]) -> SemanticEmbeddingBatch:
        """Embed non-empty text in caller order."""
        ...


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
    minimum_semantic_similarity: float = 0.25
    semantic_duplicate_threshold: float = 0.8
    retain_cross_source_corroboration: bool = False
    semantic_encoder_id: str | None = None
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

    @field_validator("minimum_semantic_similarity")
    @classmethod
    def _validate_semantic_threshold(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("minimum semantic similarity must be within [0, 1]")
        return value

    @field_validator("method")
    @classmethod
    def _validate_method(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("synthesis method must not be empty")
        return value

    @field_validator("semantic_encoder_id")
    @classmethod
    def _validate_semantic_encoder_id(cls, value: str | None) -> str | None:
        return None if value is None else _require_artifact_id(value)

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
    semantic_similarity: float | None = None
    semantic_need_similarities: tuple[float, ...] = ()
    semantic_need_term_overlaps: tuple[int, ...] = ()
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

    @field_validator("semantic_similarity")
    @classmethod
    def _validate_semantic_similarity(cls, value: float | None) -> float | None:
        if value is not None and (not math.isfinite(value) or not -1 <= value <= 1):
            raise ValueError("semantic similarity must be finite and within [-1, 1]")
        return value

    @field_validator("semantic_need_similarities")
    @classmethod
    def _validate_semantic_need_similarities(
        cls, value: tuple[float, ...]
    ) -> tuple[float, ...]:
        if any(not math.isfinite(item) or not -1 <= item <= 1 for item in value):
            raise ValueError("semantic need similarities must be within [-1, 1]")
        return value

    @field_validator("semantic_need_term_overlaps")
    @classmethod
    def _validate_semantic_need_term_overlaps(
        cls, value: tuple[int, ...]
    ) -> tuple[int, ...]:
        if any(item < 0 for item in value):
            raise ValueError("semantic need term overlaps must not be negative")
        return value

    @model_validator(mode="after")
    def _validate_identities(self) -> Self:
        if self.semantic_similarity is None:
            if self.semantic_need_similarities or self.semantic_need_term_overlaps:
                raise ValueError("lexical synthesis points cannot carry semantic needs")
        elif (
            not self.semantic_need_similarities
            or len(self.semantic_need_similarities)
            != len(self.semantic_need_term_overlaps)
        ):
            raise ValueError("semantic synthesis point need scores must align")
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

    def __init__(
        self,
        policy: CredentialFreeSynthesisPolicy | None = None,
        *,
        semantic_encoder: SemanticEmbeddingService | None = None,
    ) -> None:
        self._policy = policy or CredentialFreeSynthesisPolicy()
        self._semantic_encoder = semantic_encoder
        actual_encoder_id = (
            None if semantic_encoder is None else semantic_encoder.model_lock_id
        )
        if self._policy.semantic_encoder_id != actual_encoder_id:
            raise ValueError(
                "synthesis policy semantic encoder identity does not match composition"
            )

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
        prose_evidence = tuple(
            item for item in evidence if not _standalone_fragment(item.exact_text)
        )
        selected_evidence = prose_evidence or evidence
        candidates = tuple(
            self._point(
                evidence=item,
                clause=clause,
                question=question,
                style=style,
            )
            for item in selected_evidence
            for clause in _ranked_clauses(question, item.exact_text)
        )
        candidates = self._semantic_rescore(question, candidates)
        candidates = tuple(item for item in candidates if "?" not in item.statement)
        sources_with_answer_bearing_clauses = {
            item.source_id
            for item in candidates
            if not _background_or_setup(item.statement)
        }
        candidates = tuple(
            item
            for item in candidates
            if not _background_or_setup(item.statement)
            or item.source_id not in sources_with_answer_bearing_clauses
        )
        method_request_terms = _METHOD_TERMS | {
            "experimental",
            "specimen",
            "specimens",
            "tissue",
            "tissues",
        }
        if style is not SynthesisStyle.methods_comparison and not (
            _terms(question) & method_request_terms
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
        if self._policy.required_sources > 1 and not re.search(
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
            item
            for item in candidates
            if item.query_term_overlap >= minimum_overlap
            or _need_term_overlap(question, item.statement) >= minimum_overlap
            or (
                item.semantic_similarity is not None
                and item.semantic_similarity
                >= self._policy.minimum_semantic_similarity
            )
            or any(item.semantic_need_term_overlaps)
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
        semantic_frontier: list[ExtractiveSynthesisPoint] = []
        if self._semantic_encoder is not None and ranked:
            need_count = len(ranked[0].semantic_need_similarities)
            for need_index in range(need_count):
                remaining = tuple(
                    item for item in ranked if item not in semantic_frontier
                )
                if not remaining or len(semantic_frontier) >= self._policy.max_points:
                    break
                best = max(
                    remaining,
                    key=lambda item: (
                        round(
                            item.semantic_need_term_overlaps[need_index] * 10
                            + item.semantic_need_similarities[need_index] * 100
                            + item.extraction_score,
                            9,
                        ),
                        item.semantic_need_term_overlaps[need_index],
                        item.semantic_need_similarities[need_index],
                        item.extraction_score,
                        -item.retrieval_rank,
                    ),
                )
                if (
                    (
                        best.semantic_need_term_overlaps[need_index] > 0
                        or best.semantic_need_similarities[need_index]
                        >= self._policy.minimum_semantic_similarity
                    )
                    and best not in semantic_frontier
                ):
                    semantic_frontier.append(best)
        ordered = [
            *semantic_frontier,
            *(item for item in ranked if item not in semantic_frontier),
        ]
        diverse: list[ExtractiveSynthesisPoint] = []
        if self._policy.required_sources > 1:
            seen_sources: set[str] = set()
            for item in ordered:
                if item.source_id not in seen_sources:
                    diverse.append(item)
                    seen_sources.add(item.source_id)
            diverse.extend(item for item in ordered if item not in diverse)
        else:
            diverse.extend(ordered)
        selected: list[ExtractiveSynthesisPoint] = []
        for item in diverse:
            if any(
                _semantically_duplicate(
                    item,
                    prior,
                    threshold=self._policy.semantic_duplicate_threshold,
                )
                for prior in selected
                if not (
                    self._policy.retain_cross_source_corroboration
                    and item.source_id != prior.source_id
                )
            ):
                continue
            selected.append(item)
            if len(selected) >= self._policy.max_points:
                break
        return tuple(selected)

    def _semantic_rescore(
        self,
        question: str,
        candidates: tuple[ExtractiveSynthesisPoint, ...],
    ) -> tuple[ExtractiveSynthesisPoint, ...]:
        if self._semantic_encoder is None or not candidates:
            return candidates
        needs = _semantic_needs(question)
        batch = self._semantic_encoder.embed(
            (*needs, *(candidate.statement for candidate in candidates))
        )
        if batch.model_lock_id != self._policy.semantic_encoder_id:
            raise ValueError("semantic embedding batch model identity drifted")
        if len(batch.vectors) != len(candidates) + len(needs):
            raise ValueError("semantic embedding output count does not match input")
        need_vectors = batch.vectors[: len(needs)]
        candidate_vectors = batch.vectors[len(needs) :]
        return tuple(
            _with_semantic_similarity(
                candidate,
                tuple(_cosine_similarity(need, vector) for need in need_vectors),
                tuple(
                    _need_term_overlap(need, candidate.statement)
                    for need in needs
                ),
            )
            for candidate, vector in zip(candidates, candidate_vectors, strict=True)
        )

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
            + _projection_reference_bonus(projection, evidence.exact_text)
            + _evidence_shape_score(quote, evidence.exact_text),
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
            "semantic_similarity": None,
            "semantic_need_similarities": (),
            "semantic_need_term_overlaps": (),
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
            semantic_similarity=None,
            semantic_need_similarities=(),
            semantic_need_term_overlaps=(),
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
        prefix = text[max(0, boundary.start() - 16) : boundary.start()]
        if _NONTERMINAL_ABBREVIATION.search(prefix):
            continue
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
    first_terms = _terms(first.statement) - _DUPLICATE_STOPWORDS
    second_terms = _terms(second.statement) - _DUPLICATE_STOPWORDS
    shorter, longer = sorted((first_terms, second_terms), key=len)
    if shorter and len(shorter & longer) / len(shorter) >= 0.8:
        return True
    first_numbers = frozenset(_NUMBER.findall(first.statement.casefold()))
    second_numbers = frozenset(_NUMBER.findall(second.statement.casefold()))
    if not first_numbers & second_numbers:
        return False
    shared = first_terms & second_terms
    union = first_terms | second_terms
    return len(shared) >= 5 and len(shared) / len(union) >= 0.2


def _cosine_similarity(
    first: tuple[float, ...],
    second: tuple[float, ...],
) -> float:
    if not first or len(first) != len(second):
        raise ValueError("semantic embedding vectors must be non-empty and aligned")
    if any(not math.isfinite(value) for value in (*first, *second)):
        raise ValueError("semantic embedding vectors must be finite")
    first_norm = math.sqrt(sum(value * value for value in first))
    second_norm = math.sqrt(sum(value * value for value in second))
    if first_norm == 0 or second_norm == 0:
        raise ValueError("semantic embedding vectors must have non-zero norm")
    measured = sum(left * right for left, right in zip(first, second, strict=True)) / (
        first_norm * second_norm
    )
    return max(-1.0, min(1.0, measured))


def _with_semantic_similarity(
    point: ExtractiveSynthesisPoint,
    need_similarities: tuple[float, ...],
    need_term_overlaps: tuple[int, ...],
) -> ExtractiveSynthesisPoint:
    similarity = max(need_similarities)
    payload = point.model_dump(mode="json", exclude={"artifact_id"})
    payload["semantic_similarity"] = similarity
    payload["semantic_need_similarities"] = need_similarities
    payload["semantic_need_term_overlaps"] = need_term_overlaps
    payload["extraction_score"] = point.extraction_score + max(
        0, round(similarity * 120)
    )
    return ExtractiveSynthesisPoint(
        artifact_id=_artifact_id(payload),
        **payload,
    )


def _lexical_concepts(text: str) -> frozenset[str]:
    concepts = set()
    for term in _terms(text) - _DUPLICATE_STOPWORDS:
        for suffix in ("ing", "ed", "es", "s"):
            if term.endswith(suffix) and len(term) > len(suffix) + 3:
                term = term[: -len(suffix)]
                break
        concepts.add(term)
    return frozenset(concepts)


def _need_term_overlap(need: str, statement: str) -> int:
    primary_need, separator, relation_context = need.partition(" in relation to ")
    need_terms = _terms(primary_need)
    context_terms = _terms(relation_context) if separator else frozenset()
    statement_terms = _terms(statement)
    score = len(_lexical_concepts(primary_need) & _lexical_concepts(statement))
    for triggers, expressions in _QUESTION_CONCEPTS:
        if need_terms & triggers and statement_terms & expressions:
            score += 1
        if context_terms & triggers and statement_terms & expressions:
            score += 1
    if need_terms & {"amount", "quantitative", "quantity"} and _NUMBER.search(
        statement
    ):
        score += 2
    if "advantage" in need_terms and _ADVANTAGE_CUE.search(statement):
        score += 8
    if need_terms & {"best", "greatest", "highest", "most"} and (
        _SUPERLATIVE_RESULT_CUE.search(statement)
    ):
        score += 16
    return score


def _semantic_needs(question: str) -> tuple[str, ...]:
    """Derive general coordinated evidence needs without corpus-specific labels."""

    normalized = " ".join(question.strip().rstrip("?").split())
    clauses = tuple(
        part.strip()
        for part in re.split(
            r"\s*;\s*|,?\s+and\s+(?=(?:how|what|where|which|why)\b)",
            normalized,
            flags=re.IGNORECASE,
        )
        if part.strip()
    )
    needs: list[str] = []
    topic_context = clauses[0] if len(clauses) > 1 else None
    for clause_index, clause in enumerate(clauses):
        expanded = _coordinated_question_needs(clause)
        for need in expanded:
            if clause_index > 0 and topic_context is not None:
                need = f"{need} in relation to {topic_context}"
            needs.append(need)
    across = re.search(
        r"\bacross\s+(?P<items>.+?),\s+(?P<predicate>(?:how|what|where|which|why)\b.+)$",
        normalized,
        flags=re.IGNORECASE,
    )
    if across is not None:
        needs = [
            f"{item} {across.group('predicate')}"
            for item in _split_coordinated_items(across.group("items"))
        ]
    based_on = re.search(r"\bbased on (?P<items>.+)$", normalized, re.IGNORECASE)
    if based_on is not None:
        prefix = normalized[: based_on.start()].strip(" ,")
        needs.extend(
            f"{prefix} based on {item}"
            for item in _split_coordinated_items(based_on.group("items"))
        )
    return tuple(dict.fromkeys(need for need in needs if need)) or (normalized,)


def _coordinated_question_needs(clause: str) -> tuple[str, ...]:
    study_list = re.match(
        r"^(?:how|what|why)\s+do\s+(?:the\s+)?(?P<items>.+?)\s+"
        r"(?P<collective>articles|papers|sources|studies)\s+(?P<predicate>.+)$",
        clause,
        flags=re.IGNORECASE,
    )
    if study_list is not None:
        items = _split_coordinated_items(study_list.group("items"))
        if len(items) > 1:
            collective = study_list.group("collective")
            singular = collective[:-1] if collective.endswith("s") else collective
            return tuple(
                f"{item} {singular} {study_list.group('predicate')}" for item in items
            )
    requested_slots = re.match(
        r"^(?:how|what|where|which|why)\s+(?P<items>.+?)\s+"
        r"(?P<verb>are|bounded|did|does|is|produced|remained|reported|"
        r"supported|was|were)\b(?P<predicate>.*)$",
        clause,
        flags=re.IGNORECASE,
    )
    if requested_slots is None:
        return (clause,)
    items = _split_coordinated_items(requested_slots.group("items"))
    if len(items) <= 1:
        return (clause,)
    verb = requested_slots.group("verb")
    predicate = requested_slots.group("predicate").strip()
    return tuple(
        " ".join(part for part in (item, verb, predicate) if part) for item in items
    )


def _split_coordinated_items(value: str) -> tuple[str, ...]:
    return tuple(
        item.strip()
        for item in re.split(
            r",\s*(?:and\s+|or\s+)?|\s+(?:and|or)\s+",
            value,
            flags=re.IGNORECASE,
        )
        if item.strip()
    )


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


def _evidence_shape_score(quote: str, reference_text: str) -> int:
    """Demote standalone headings and glossary fragments without hiding them."""

    normalized = " ".join(quote.split())
    if normalized != " ".join(reference_text.split()):
        return 0
    terms = _terms(normalized) - _DUPLICATE_STOPWORDS
    if len(terms) <= 4 or (len(terms) <= 16 and normalized[-1:] not in {".", "!", "?"}):
        return -64
    return 0


def _background_or_setup(statement: str) -> bool:
    return bool(
        _AIM_CUE.search(statement)
        or _SETUP_CUE.search(statement)
        or _BACKGROUND_CUE.search(statement)
    )


def _standalone_fragment(statement: str) -> bool:
    normalized = " ".join(statement.split())
    terms = _terms(normalized) - _DUPLICATE_STOPWORDS
    return len(terms) <= 16 and normalized[-1:] not in {".", "!", "?"}


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
    if question_terms & {
        "quantitative",
        "amount",
        "advantage",
        "difference",
    } and _NUMBER.search(statement):
        score += 8
    if _RESULT_CUE.search(statement):
        score += 14
    if _DECISIVE_CUE.search(statement):
        score += 18
    if question_terms & {
        "recommend",
        "recommended",
        "recommendation",
        "should",
    } and _RECOMMENDATION_CUE.search(statement):
        score += 28
    if question_terms & {"necessary", "necessity", "whether"} and (
        _DECISIVE_CUE.search(statement) or _COMPARISON_CUE.search(statement)
    ):
        score += 22
    if question_terms & {"test", "tested", "how"} and (
        _COMPARISON_CUE.search(statement) and _METHOD_CUE.search(statement)
    ):
        score += 20
    if question_terms & {
        "prove",
        "proof",
        "authenticate",
        "authenticating",
        "distinguish",
    } and re.search(
        r"\b(?:alone|cannot|indistinguishable|not reliable|not sufficient|solely)\b",
        statement,
        flags=re.IGNORECASE,
    ):
        score += 120
    if question_terms & {
        "oldest",
        "earliest",
        "latest",
        "newest",
    } and _NUMBER.search(statement):
        score += 18
    if question_terms & {"imply", "implication", "conclusion"} and (
        _RESULT_CUE.search(statement)
        or re.search(
            r"\b(?:conclusion|conclude|therefore)\b", statement, re.IGNORECASE
        )
    ):
        score += 18
    if question_terms & {"limit", "limits", "limitation", "limitations"} and (
        role in {EvidenceRole.limitation, EvidenceRole.counterevidence}
        or re.search(
            r"\b(?:below|caution|lower than|remain(?:s|ed)? to be determined|"
            r"unresolved)\b",
            statement,
            flags=re.IGNORECASE,
        )
    ):
        score += 24
    if "why" in question_terms and re.search(
        r"\b(?:because|cannot|due to|indistinguishable|so|therefore)\b",
        statement,
        flags=re.IGNORECASE,
    ):
        score += 18
    if _AIM_CUE.search(statement):
        score -= 36
    if _SETUP_CUE.search(statement):
        score -= 34
    if _BACKGROUND_CUE.search(statement):
        score -= 24
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
    based_on = re.search(
        r"\bbased on (?P<items>[^?]+)", normalized, flags=re.IGNORECASE
    )
    if based_on is not None:
        items = re.split(
            r",\s*(?:and\s+|or\s+)?|\s+(?:and|or)\s+",
            based_on.group("items"),
        )
        count = len(tuple(item for item in items if item.strip()))
        if count >= 2:
            return min(6, count)
    if re.search(r"\b[^,?]+\s+and\s+[^,?]+\s+studies\b", normalized):
        return 2
    cross_source = (
        re.search(r"\bacross\b.*\b(?:papers|sources|studies|articles)\b", normalized)
        or re.search(r"\b(?:papers|sources|studies|articles)\b.*\bacross\b", normalized)
        or re.search(
            r"\b(?:both|two)\b.*\b(?:papers|sources|studies|articles)\b", normalized
        )
        or re.search(
            r"\bcompare\b.*\b(?:papers|sources|studies|articles)\b", normalized
        )
        or re.search(
            r"\b(?:combine|disagree|reconcile)\b.*"
            r"\b(?:papers|sources|studies|articles)\b",
            normalized,
        )
        or re.search(
            r"\b(?:papers|sources|studies|articles)\b.*"
            r"\b(?:combine|disagree|reconcile)\b",
            normalized,
        )
    )
    return 2 if cross_source else 1


def recommended_point_count(question: str) -> int:
    """Bound answer points while retaining explicitly requested source contexts."""

    sources = required_source_count(question)
    requested_terms = _terms(question)
    limitation_allowance = (
        2
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
    "SemanticEmbeddingBatch",
    "SemanticEmbeddingService",
    "SynthesisOutcome",
    "SynthesisStyle",
    "infer_synthesis_style",
    "recommended_point_count",
    "required_source_count",
]
