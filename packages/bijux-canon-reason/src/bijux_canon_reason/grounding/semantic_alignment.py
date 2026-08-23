# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Conservative credential-free semantic alignment for claim evidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re

from bijux_canon_reason.grounding.semantic_projection import (
    EvidenceProjectionMethod,
    project_evidence_text,
)

_WORD = re.compile(r"[^\W_]+", flags=re.UNICODE)
_CLAUSE_BOUNDARY = re.compile(r"(?<=[.!?;])\s+")
_QUANTITY = re.compile(
    r"\b(?:(?:approximately|at\s+least|below|higher\s+than|less\s+than|"
    r"lower\s+than|more\s+than|over|up\s+to|~)\s+)?"
    r"\d[\d,.]*(?:[–-]\d[\d,.]*)?\s*(?:%|[–-]?fold|times?)?"
    r"(?![\w%–-])",
    flags=re.IGNORECASE,
)
_SCOPE_NARROWING = re.compile(
    r"\b(?:at\s+least\s+one|only|some|subset|tested\s+samples?|"
    r"tested\s+specimens?|within\s+the\s+study)\b",
    flags=re.IGNORECASE,
)
_POSSIBLE = re.compile(
    r"\b(?:can|could|may|might|possible|potentially)\b", flags=re.IGNORECASE
)
_RECOMMENDATION = re.compile(
    r"\b(?:ought\s+to|recommend(?:ed|s)?|should)\b", flags=re.IGNORECASE
)
_PROBABLE = re.compile(r"\b(?:likely|probably|suggest(?:s|ed)?)\b", flags=re.IGNORECASE)
_UNCERTAIN = re.compile(
    r"\b(?:ambiguous|uncertain|unclear|unknown|remain(?:s|ed)?\s+to\s+be\s+"
    r"determined)\b",
    flags=re.IGNORECASE,
)
_GOVERNING_NEGATION = re.compile(
    r"\b(?:cannot|denied|denies|false|failed|no|not|never)\b"
    r"(?:\W+[^\W_]+){0,8}\W*$",
    flags=re.IGNORECASE,
)
_NEGATIONS = frozenset(
    {
        "cannot",
        "denied",
        "denies",
        "false",
        "failed",
        "no",
        "not",
        "never",
        "neither",
        "nor",
        "without",
    }
)
_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "by",
        "did",
        "do",
        "does",
        "for",
        "from",
        "had",
        "has",
        "have",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "were",
        "with",
    }
)


class ConservativeSemanticRelation(StrEnum):
    """A relation established without a generative semantic verifier."""

    direct_support = "direct_support"
    opposition = "opposition"
    ambiguity = "ambiguity"
    irrelevance = "irrelevance"
    insufficiency = "insufficiency"


@dataclass(frozen=True, slots=True)
class ConservativeSemanticAssessment:
    """Measured conservative relation and the features used to establish it."""

    relation: ConservativeSemanticRelation
    claim_term_coverage: float
    exact_claim_span: bool
    claim_negated: bool
    evidence_negated: bool
    rationale_code: str


def assess_conservative_alignment(
    *,
    claim: str,
    evidence: str,
    minimum_evidence_terms: int,
    related_claim_term_coverage: float,
    support_claim_term_coverage: float,
    opposition_claim_term_coverage: float,
) -> ConservativeSemanticAssessment:
    """Classify a relation only when ordered terms and qualifiers align."""

    claim_terms = _term_sequence(claim)
    evidence_window = _best_semantic_window(claim_terms, evidence)
    evidence_terms = _term_sequence(evidence_window)
    claim_words = frozenset(claim_terms)
    evidence_words = frozenset(evidence_terms)
    exact_span = claim in evidence
    verified_projection = claim in {
        projection.statement
        for projection in project_evidence_text(evidence)
        if projection.method is not EvidenceProjectionMethod.exact_clause
    }
    claim_negated = _negated(claim)
    exact_context = claim
    if exact_span:
        exact_context = _exact_span_context(claim, evidence)
        evidence_negated = _negated(exact_context)
    elif verified_projection:
        evidence_negated = claim_negated
    else:
        evidence_negated = _negated(evidence_window)
    coverage = (
        len(claim_words & evidence_words) / len(claim_words) if claim_words else 0.0
    )
    relation: ConservativeSemanticRelation
    rationale: str
    if len(evidence_words) < minimum_evidence_terms:
        relation = ConservativeSemanticRelation.insufficiency
        rationale = "evidence_below_minimum_terms"
    elif exact_span and claim_negated == evidence_negated:
        relation = ConservativeSemanticRelation.direct_support
        rationale = "claim_is_exact_evidence_span"
    elif exact_span and _modality_supports(claim, exact_context):
        relation = ConservativeSemanticRelation.opposition
        rationale = "exact_claim_span_has_opposite_negation"
    elif exact_span:
        relation = ConservativeSemanticRelation.ambiguity
        rationale = "exact_span_opposite_negation_below_claim_modality"
    elif verified_projection and claim_negated == evidence_negated:
        relation = ConservativeSemanticRelation.direct_support
        rationale = "claim_is_verified_conservative_projection"
    elif verified_projection:
        relation = ConservativeSemanticRelation.opposition
        rationale = "verified_projection_has_opposite_negation"
    elif (
        claim_negated != evidence_negated
        and coverage >= opposition_claim_term_coverage
        and _semantic_features_align(
            claim, evidence_window, claim_terms, evidence_terms
        )
    ):
        relation = ConservativeSemanticRelation.opposition
        rationale = "aligned_proposition_has_opposite_negation"
    elif (
        claim_negated == evidence_negated
        and coverage >= support_claim_term_coverage
        and _semantic_features_align(
            claim, evidence_window, claim_terms, evidence_terms
        )
    ):
        relation = ConservativeSemanticRelation.direct_support
        rationale = "conservative_lexical_semantic_alignment"
    elif coverage < related_claim_term_coverage:
        relation = ConservativeSemanticRelation.irrelevance
        rationale = "claim_terms_unrelated_to_evidence"
    else:
        relation = ConservativeSemanticRelation.ambiguity
        rationale = "semantic_scope_or_qualifiers_not_aligned"
    return ConservativeSemanticAssessment(
        relation=relation,
        claim_term_coverage=coverage,
        exact_claim_span=exact_span,
        claim_negated=claim_negated,
        evidence_negated=evidence_negated,
        rationale_code=rationale,
    )


def _term_sequence(text: str) -> tuple[str, ...]:
    return tuple(
        _stem(word)
        for word in (item.casefold() for item in _WORD.findall(text))
        if word not in _STOP_WORDS and word not in _NEGATIONS
    )


def _best_semantic_window(claim_terms: tuple[str, ...], evidence: str) -> str:
    windows = tuple(
        window.strip() for window in _CLAUSE_BOUNDARY.split(evidence) if window.strip()
    ) or (evidence,)
    claim_words = frozenset(claim_terms)
    return max(
        windows,
        key=lambda window: (
            len(claim_words.intersection(_term_sequence(window))),
            -len(_term_sequence(window)),
        ),
    )


def _semantic_features_align(
    claim: str,
    evidence: str,
    claim_terms: tuple[str, ...],
    evidence_terms: tuple[str, ...],
) -> bool:
    if not _ordered_subset(claim_terms, evidence_terms):
        return False
    if not set(_quantities(claim)).issubset(_quantities(evidence)):
        return False
    if not set(_scope_markers(evidence)).issubset(_scope_markers(claim)):
        return False
    return _modality_supports(claim, evidence)


def _ordered_subset(needles: tuple[str, ...], haystack: tuple[str, ...]) -> bool:
    if not needles:
        return False
    cursor = iter(haystack)
    return all(any(candidate == needle for candidate in cursor) for needle in needles)


def _quantities(text: str) -> tuple[str, ...]:
    return tuple(
        re.sub(r"\s+", " ", match.group().casefold()).strip()
        for match in _QUANTITY.finditer(text)
    )


def _scope_markers(text: str) -> tuple[str, ...]:
    return tuple(match.group().casefold() for match in _SCOPE_NARROWING.finditer(text))


@dataclass(frozen=True, slots=True)
class _Modality:
    kind: str
    strength: int


def _modality(text: str) -> _Modality:
    if _RECOMMENDATION.search(text):
        return _Modality("recommendation", 1)
    if _UNCERTAIN.search(text):
        return _Modality("epistemic", 0)
    if _POSSIBLE.search(text):
        return _Modality("epistemic", 1)
    if _PROBABLE.search(text):
        return _Modality("epistemic", 2)
    return _Modality("epistemic", 3)


def _modality_supports(claim: str, evidence: str) -> bool:
    claim_modality = _modality(claim)
    evidence_modality = _modality(evidence)
    return (
        claim_modality.kind == evidence_modality.kind
        and evidence_modality.strength >= claim_modality.strength
    )


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) > len(suffix) + 3:
            return word[: -len(suffix)]
    return word


def _negated(text: str) -> bool:
    return bool(
        _NEGATIONS.intersection(item.casefold() for item in _WORD.findall(text))
    )


def _exact_span_context(claim: str, evidence: str) -> str:
    start = evidence.find(claim)
    if start < 0:
        return claim
    governing_prefix = evidence[max(0, start - 160) : start]
    if _GOVERNING_NEGATION.search(governing_prefix) is None:
        return claim
    return f"{governing_prefix}{claim}"


__all__ = [
    "ConservativeSemanticAssessment",
    "ConservativeSemanticRelation",
    "assess_conservative_alignment",
]
