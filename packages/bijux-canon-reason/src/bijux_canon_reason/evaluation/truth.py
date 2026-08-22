# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Immutable, independently reviewed evaluation truth models."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
import hashlib
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from bijux_canon_reason.core.models.base import StableModel

Identifier = Annotated[
    str,
    StringConstraints(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"),
]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class EvaluationSplit(StrEnum):
    """Supported evaluation partitions."""

    development = "development"
    heldout = "heldout"


class ClaimTruthClass(StrEnum):
    """Adjudicated atomic-claim classes."""

    expected = "expected"
    optional = "optional"
    opposed = "opposed"
    forbidden = "forbidden"


class CitationTruthRelation(StrEnum):
    """Direct relation between an exact evidence span and an atomic claim."""

    supports = "supports"
    opposes = "opposes"
    limits = "limits"
    insufficient = "insufficient"


class AbstentionExpectation(StrEnum):
    """Expected answer behavior for an evaluation claim or case."""

    required = "required"
    allowed = "allowed"
    prohibited = "prohibited"


class TruthProvenance(StableModel):
    """Human-review and immutable-input lineage for truth labels."""

    schema_version: Literal["bijux.canon.evaluation.truth-provenance.v1"] = (
        "bijux.canon.evaluation.truth-provenance.v1"
    )
    reviewer_ids: tuple[Identifier, ...] = Field(min_length=1)
    reviewed_on: date
    review_method: NonEmptyText
    source_identity_sha256: Sha256
    data_identity_sha256: Sha256
    system_output_consulted: Literal[False] = False

    @model_validator(mode="after")
    def _require_distinct_reviewers(self) -> TruthProvenance:
        if len(set(self.reviewer_ids)) != len(self.reviewer_ids):
            raise ValueError("truth provenance reviewer IDs must be unique")
        return self


class ExactEvidenceLocator(StableModel):
    """Content-addressed exact source span used by an evaluation judgment."""

    schema_version: Literal["bijux.canon.evaluation.exact-locator.v1"] = (
        "bijux.canon.evaluation.exact-locator.v1"
    )
    locator_id: Identifier
    source_id: Identifier
    source_uri: NonEmptyText
    source_sha256: Sha256
    chunk_id: NonEmptyText
    character_start: int = Field(ge=0)
    character_end: int = Field(gt=0)
    exact_text: Annotated[str, StringConstraints(min_length=1)]
    exact_text_sha256: Sha256

    @model_validator(mode="after")
    def _validate_exact_span(self) -> ExactEvidenceLocator:
        if self.character_end <= self.character_start:
            raise ValueError("exact locator end must follow its start")
        if self.character_end - self.character_start != len(self.exact_text):
            raise ValueError("exact locator bounds must match the retained text")
        digest = hashlib.sha256(self.exact_text.encode("utf-8")).hexdigest()
        if digest != self.exact_text_sha256:
            raise ValueError("exact locator text hash mismatch")
        return self


class EvaluationQuery(StableModel):
    """Versioned question whose labels are independent of system outputs."""

    schema_version: Literal["bijux.canon.evaluation.query.v1"] = (
        "bijux.canon.evaluation.query.v1"
    )
    query_id: Identifier
    text: NonEmptyText
    provenance: TruthProvenance


class QrelJudgment(StableModel):
    """Graded source-first relevance judgment for one exact locator."""

    schema_version: Literal["bijux.canon.evaluation.qrel.v1"] = (
        "bijux.canon.evaluation.qrel.v1"
    )
    qrel_id: Identifier
    query_id: Identifier
    relevance_grade: int = Field(ge=0, le=3)
    locator: ExactEvidenceLocator
    rationale: NonEmptyText
    provenance: TruthProvenance
    system_ranking_consulted: Literal[False] = False


class CitationTruthLabel(StableModel):
    """Reviewed claim-to-qrel relation; mere evidence presence is insufficient."""

    schema_version: Literal["bijux.canon.evaluation.citation-truth.v1"] = (
        "bijux.canon.evaluation.citation-truth.v1"
    )
    citation_label_id: Identifier
    qrel_id: Identifier
    relation: CitationTruthRelation
    rationale: NonEmptyText
    provenance: TruthProvenance


class AtomicClaimTruth(StableModel):
    """Reviewed atomic answer claim and its expected answer behavior."""

    schema_version: Literal["bijux.canon.evaluation.atomic-claim-truth.v1"] = (
        "bijux.canon.evaluation.atomic-claim-truth.v1"
    )
    claim_truth_id: Identifier
    query_id: Identifier
    statement: NonEmptyText
    claim_class: ClaimTruthClass
    expected_in_answer: bool
    abstention_expectation: AbstentionExpectation
    citations: tuple[CitationTruthLabel, ...] = Field(min_length=1)
    rationale: NonEmptyText
    provenance: TruthProvenance

    @model_validator(mode="after")
    def _validate_class_policy(self) -> AtomicClaimTruth:
        relations = {citation.relation for citation in self.citations}
        if len({citation.citation_label_id for citation in self.citations}) != len(
            self.citations
        ):
            raise ValueError("claim citation label IDs must be unique")
        if self.claim_class is ClaimTruthClass.expected:
            if (
                not self.expected_in_answer
                or CitationTruthRelation.supports not in relations
            ):
                raise ValueError("expected claims must be answer-bearing and supported")
            if self.abstention_expectation is not AbstentionExpectation.prohibited:
                raise ValueError("expected claims must prohibit abstention")
        elif self.claim_class is ClaimTruthClass.optional:
            if (
                self.expected_in_answer
                or CitationTruthRelation.supports not in relations
            ):
                raise ValueError("optional claims must be non-required and supported")
        elif self.claim_class is ClaimTruthClass.opposed:
            if (
                self.expected_in_answer
                or CitationTruthRelation.opposes not in relations
            ):
                raise ValueError("opposed claims must be excluded and directly opposed")
            if self.abstention_expectation is not AbstentionExpectation.required:
                raise ValueError("opposed claims must require abstention")
        elif self.claim_class is ClaimTruthClass.forbidden:
            if self.expected_in_answer or not relations.intersection(
                {CitationTruthRelation.limits, CitationTruthRelation.opposes}
            ):
                raise ValueError(
                    "forbidden claims require limiting or opposing evidence"
                )
            if self.abstention_expectation is not AbstentionExpectation.required:
                raise ValueError("forbidden claims must require abstention")
        return self


class ConflictExpectation(StableModel):
    """Reviewed expectation for retaining conflicting evidence or claims."""

    conflict_expected: bool
    claim_truth_ids: tuple[Identifier, ...] = ()
    rationale: NonEmptyText

    @model_validator(mode="after")
    def _validate_conflict_members(self) -> ConflictExpectation:
        if len(set(self.claim_truth_ids)) != len(self.claim_truth_ids):
            raise ValueError("conflict claim IDs must be unique")
        if self.conflict_expected and len(self.claim_truth_ids) < 2:
            raise ValueError("an expected conflict requires at least two claims")
        if not self.conflict_expected and self.claim_truth_ids:
            raise ValueError("non-conflict cases cannot declare conflict members")
        return self


class EvaluationCaseTruth(StableModel):
    """Complete independently reviewed truth for one evaluation case."""

    schema_version: Literal["bijux.canon.evaluation.case-truth.v1"] = (
        "bijux.canon.evaluation.case-truth.v1"
    )
    case_id: Identifier
    split: EvaluationSplit
    archetype: Identifier
    difficulty: Identifier
    evidence_condition: Identifier
    query: EvaluationQuery
    qrels: tuple[QrelJudgment, ...] = Field(min_length=1)
    claims: tuple[AtomicClaimTruth, ...] = Field(min_length=1)
    conflict: ConflictExpectation
    abstention_expectation: AbstentionExpectation
    provenance: TruthProvenance
    heldout_labels_available_to_tuning: Literal[False] = False
    system_output_may_define_truth: Literal[False] = False

    @model_validator(mode="after")
    def _validate_references(self) -> EvaluationCaseTruth:
        qrel_ids = {qrel.qrel_id for qrel in self.qrels}
        if len(qrel_ids) != len(self.qrels):
            raise ValueError("evaluation case qrel IDs must be unique")
        if any(qrel.query_id != self.query.query_id for qrel in self.qrels):
            raise ValueError("every qrel must reference the case query")
        claim_ids = {claim.claim_truth_id for claim in self.claims}
        if len(claim_ids) != len(self.claims):
            raise ValueError("evaluation case claim IDs must be unique")
        if any(claim.query_id != self.query.query_id for claim in self.claims):
            raise ValueError("every claim must reference the case query")
        cited_qrels = {
            citation.qrel_id for claim in self.claims for citation in claim.citations
        }
        if not cited_qrels.issubset(qrel_ids):
            raise ValueError("claim citation truth references an unknown qrel")
        if not set(self.conflict.claim_truth_ids).issubset(claim_ids):
            raise ValueError("conflict expectation references an unknown claim")
        return self


__all__ = [
    "AbstentionExpectation",
    "AtomicClaimTruth",
    "CitationTruthLabel",
    "CitationTruthRelation",
    "ClaimTruthClass",
    "ConflictExpectation",
    "EvaluationCaseTruth",
    "EvaluationQuery",
    "EvaluationSplit",
    "ExactEvidenceLocator",
    "Identifier",
    "NonEmptyText",
    "QrelJudgment",
    "Sha256",
    "TruthProvenance",
]
