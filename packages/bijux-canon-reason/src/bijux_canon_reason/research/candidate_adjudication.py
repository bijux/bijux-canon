# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Classify retrieved research candidates against exact claims and scope."""

from __future__ import annotations

from enum import StrEnum
import math
import re
from typing import Literal, Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.evidence_packets import CitationEvidence
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)
from bijux_canon_reason.grounding.semantic_alignment import (
    ConservativeSemanticRelation,
    assess_conservative_alignment,
)

_LIMITATION = re.compile(
    r"\b(?:boundary|caveat|constraint|fail(?:ed|ure)?|limit(?:ed|ation|ations)?|"
    r"less than|below|uncertain(?:ty)?|cannot|could not|did not|"
    r"small sample|scope)\b",
    re.IGNORECASE,
)


class ResearchCandidateRelation(StrEnum):
    """Adjudicated semantic relationship to an exact answer need."""

    SUPPORTING = "supporting"
    OPPOSING = "opposing"
    LIMITING = "limiting"
    IRRELEVANT = "irrelevant"
    AMBIGUOUS = "ambiguous"
    UNCLASSIFIED = "unclassified"


class CandidateClassificationMethod(StrEnum):
    """Authority used to reach or withhold a candidate relation."""

    DETERMINISTIC_SEMANTIC = "deterministic_semantic"
    DETERMINISTIC_STRUCTURED_CONSENSUS = "deterministic_structured_consensus"
    STRUCTURED_CONSENSUS = "structured_consensus"
    ADJUDICATOR_DISAGREEMENT = "adjudicator_disagreement"


class CandidateAdjudicationPolicy(StableModel):
    """Conservative semantic and materiality thresholds."""

    schema_version: Literal["bijux.canon.reason.candidate_policy.v1"] = (
        "bijux.canon.reason.candidate_policy.v1"
    )
    minimum_evidence_terms: int = 3
    related_claim_term_coverage: float = 0.35
    support_claim_term_coverage: float = 0.75
    opposition_claim_term_coverage: float = 0.8
    structured_minimum_confidence: float = 0.8
    material_minimum_confidence: float = 0.35

    @model_validator(mode="after")
    def _validate_policy(self) -> Self:
        values = (
            self.related_claim_term_coverage,
            self.support_claim_term_coverage,
            self.opposition_claim_term_coverage,
            self.structured_minimum_confidence,
            self.material_minimum_confidence,
        )
        if self.minimum_evidence_terms < 1 or any(
            not math.isfinite(value) or not 0 <= value <= 1 for value in values
        ):
            raise ValueError("candidate adjudication policy bounds are invalid")
        if self.support_claim_term_coverage < self.related_claim_term_coverage:
            raise ValueError("support threshold cannot be weaker than relatedness")
        if self.opposition_claim_term_coverage < self.related_claim_term_coverage:
            raise ValueError("opposition threshold cannot be weaker than relatedness")
        return self

    @property
    def artifact_id(self) -> str:
        """Return the complete policy identity."""
        return content_artifact_id(self.model_dump(mode="json"))


class StructuredCandidateJudgment(StableModel):
    """One optional typed evaluator judgment with exact input binding."""

    artifact_id: str
    evaluator_id: str
    requirement_artifact_id: str
    claim_artifact_id: str | None
    evidence_artifact_id: str
    relation: ResearchCandidateRelation
    confidence: float
    entity_aligned: bool
    scope_aligned: bool
    qualifier_aligned: bool
    negation_aligned: bool
    rationale: str

    @field_validator(
        "artifact_id",
        "requirement_artifact_id",
        "claim_artifact_id",
        "evidence_artifact_id",
    )
    @classmethod
    def _validate_optional_id(cls, value: str | None) -> str | None:
        return None if value is None else require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_judgment(self) -> Self:
        if (
            not self.evaluator_id
            or not self.rationale
            or not math.isfinite(self.confidence)
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("structured candidate judgment is invalid")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("structured candidate judgment identity does not match")
        return self


class ResearchCandidateClassification(StableModel):
    """One exact citation classified once against one requirement and claim."""

    schema_version: Literal["bijux.canon.reason.candidate_classification.v1"] = (
        "bijux.canon.reason.candidate_classification.v1"
    )
    artifact_id: str
    requirement_artifact_id: str
    claim_artifact_id: str | None
    evidence_artifact_id: str
    locator_artifact_id: str
    exact_text_sha256: str
    relation: ResearchCandidateRelation
    rationale: str
    method: CandidateClassificationMethod
    confidence: float
    material: bool
    semantic_coverage: float
    judgment_artifact_ids: tuple[str, ...]

    @field_validator(
        "artifact_id",
        "requirement_artifact_id",
        "claim_artifact_id",
        "evidence_artifact_id",
        "locator_artifact_id",
    )
    @classmethod
    def _validate_optional_id(cls, value: str | None) -> str | None:
        return None if value is None else require_artifact_id(value)

    @field_validator("judgment_artifact_ids")
    @classmethod
    def _validate_judgment_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("candidate judgments must be unique")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_classification(self) -> Self:
        if (
            not self.rationale
            or any(
                not math.isfinite(value) or not 0 <= value <= 1
                for value in (self.confidence, self.semantic_coverage)
            )
        ):
            raise ValueError("candidate classification confidence is invalid")
        if self.relation is ResearchCandidateRelation.IRRELEVANT and self.material:
            raise ValueError("irrelevant evidence cannot be material")
        if self.relation in {
            ResearchCandidateRelation.AMBIGUOUS,
            ResearchCandidateRelation.UNCLASSIFIED,
        } and not self.material:
            raise ValueError("unresolved candidate relations must remain material")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("candidate classification identity does not match")
        return self


class DuplicateResearchCandidate(StableModel):
    """Candidate omitted because identical text was already classified."""

    evidence_artifact_id: str
    canonical_evidence_artifact_id: str
    exact_text_sha256: str

    @field_validator("evidence_artifact_id", "canonical_evidence_artifact_id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        return require_artifact_id(value)


class CandidateAdjudicationReport(StableModel):
    """Complete classification coverage for one material retrieval result."""

    schema_version: Literal["bijux.canon.reason.candidate_adjudication.v1"] = (
        "bijux.canon.reason.candidate_adjudication.v1"
    )
    artifact_id: str
    requirement_artifact_id: str
    claim_artifact_id: str | None
    policy_artifact_id: str
    input_evidence_artifact_ids: tuple[str, ...]
    classifications: tuple[ResearchCandidateClassification, ...]
    duplicates: tuple[DuplicateResearchCandidate, ...]
    material_unclassified_evidence_artifact_ids: tuple[str, ...]

    @field_validator(
        "artifact_id",
        "requirement_artifact_id",
        "claim_artifact_id",
        "policy_artifact_id",
    )
    @classmethod
    def _validate_optional_id(cls, value: str | None) -> str | None:
        return None if value is None else require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_report(self) -> Self:
        classified = {item.evidence_artifact_id for item in self.classifications}
        duplicates = {item.evidence_artifact_id for item in self.duplicates}
        if classified & duplicates or classified | duplicates != set(
            self.input_evidence_artifact_ids
        ):
            raise ValueError("every candidate must be classified or deduplicated once")
        unresolved = tuple(
            item.evidence_artifact_id
            for item in self.classifications
            if item.material
            and item.relation is ResearchCandidateRelation.UNCLASSIFIED
        )
        if self.material_unclassified_evidence_artifact_ids != unresolved:
            raise ValueError("material unclassified candidate set is incomplete")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("candidate adjudication report identity does not match")
        return self


class ResearchCandidateAdjudicationService:
    """Classify exact retrieved text without trusting retrieval query intent."""

    def __init__(self, policy: CandidateAdjudicationPolicy | None = None) -> None:
        self.policy = policy or CandidateAdjudicationPolicy()

    def classify(
        self,
        *,
        requirement_artifact_id: str,
        requirement_kind: str,
        target_statement: str,
        claim_artifact_id: str | None,
        candidates: tuple[CitationEvidence, ...],
        judgments: tuple[StructuredCandidateJudgment, ...] = (),
    ) -> CandidateAdjudicationReport:
        """Classify every unique candidate and retain duplicate provenance."""
        require_artifact_id(requirement_artifact_id)
        if claim_artifact_id is not None:
            require_artifact_id(claim_artifact_id)
        normalized_target = " ".join(target_statement.split())
        if not normalized_target:
            raise ValueError("candidate adjudication needs a target statement")
        input_ids = tuple(item.artifact_id for item in candidates)
        if len(input_ids) != len(set(input_ids)):
            raise ValueError("candidate evidence identities must be unique")
        judgment_by_evidence: dict[str, list[StructuredCandidateJudgment]] = {}
        for judgment in judgments:
            if (
                judgment.requirement_artifact_id != requirement_artifact_id
                or judgment.claim_artifact_id != claim_artifact_id
                or judgment.evidence_artifact_id not in input_ids
            ):
                raise ValueError("structured judgment references another candidate")
            judgment_by_evidence.setdefault(judgment.evidence_artifact_id, []).append(
                judgment
            )
        classifications: list[ResearchCandidateClassification] = []
        duplicates: list[DuplicateResearchCandidate] = []
        canonical_by_text: dict[str, str] = {}
        for candidate in candidates:
            canonical = canonical_by_text.get(candidate.exact_text_sha256)
            if canonical is not None:
                duplicates.append(
                    DuplicateResearchCandidate(
                        evidence_artifact_id=candidate.artifact_id,
                        canonical_evidence_artifact_id=canonical,
                        exact_text_sha256=candidate.exact_text_sha256,
                    )
                )
                continue
            canonical_by_text[candidate.exact_text_sha256] = candidate.artifact_id
            classifications.append(
                self._classify_one(
                    requirement_artifact_id=requirement_artifact_id,
                    requirement_kind=requirement_kind,
                    target_statement=normalized_target,
                    claim_artifact_id=claim_artifact_id,
                    candidate=candidate,
                    judgments=tuple(judgment_by_evidence.get(candidate.artifact_id, ())),
                )
            )
        unresolved = tuple(
            item.evidence_artifact_id
            for item in classifications
            if item.material
            and item.relation is ResearchCandidateRelation.UNCLASSIFIED
        )
        payload = {
            "schema_version": "bijux.canon.reason.candidate_adjudication.v1",
            "requirement_artifact_id": requirement_artifact_id,
            "claim_artifact_id": claim_artifact_id,
            "policy_artifact_id": self.policy.artifact_id,
            "input_evidence_artifact_ids": input_ids,
            "classifications": tuple(item.model_dump(mode="json") for item in classifications),
            "duplicates": tuple(item.model_dump(mode="json") for item in duplicates),
            "material_unclassified_evidence_artifact_ids": unresolved,
        }
        return CandidateAdjudicationReport(
            artifact_id=content_artifact_id(payload),
            requirement_artifact_id=requirement_artifact_id,
            claim_artifact_id=claim_artifact_id,
            policy_artifact_id=self.policy.artifact_id,
            input_evidence_artifact_ids=input_ids,
            classifications=tuple(classifications),
            duplicates=tuple(duplicates),
            material_unclassified_evidence_artifact_ids=unresolved,
        )

    def _classify_one(
        self,
        *,
        requirement_artifact_id: str,
        requirement_kind: str,
        target_statement: str,
        claim_artifact_id: str | None,
        candidate: CitationEvidence,
        judgments: tuple[StructuredCandidateJudgment, ...],
    ) -> ResearchCandidateClassification:
        semantic = assess_conservative_alignment(
            claim=target_statement,
            evidence=candidate.exact_text,
            minimum_evidence_terms=self.policy.minimum_evidence_terms,
            related_claim_term_coverage=self.policy.related_claim_term_coverage,
            support_claim_term_coverage=self.policy.support_claim_term_coverage,
            opposition_claim_term_coverage=self.policy.opposition_claim_term_coverage,
        )
        relation = _semantic_relation(
            semantic.relation,
            requirement_kind=requirement_kind,
            evidence_text=candidate.exact_text,
            coverage=semantic.claim_term_coverage,
            related_threshold=self.policy.related_claim_term_coverage,
        )
        rationale = semantic.rationale_code
        confidence = semantic.claim_term_coverage
        method = CandidateClassificationMethod.DETERMINISTIC_SEMANTIC
        admissible_judgments = tuple(
            item
            for item in judgments
            if item.confidence >= self.policy.structured_minimum_confidence
        )
        if admissible_judgments:
            judged_relations = {item.relation for item in admissible_judgments}
            if len(judged_relations) != 1 or (
                relation not in judged_relations
                and relation
                not in {
                    ResearchCandidateRelation.AMBIGUOUS,
                    ResearchCandidateRelation.UNCLASSIFIED,
                }
            ):
                relation = ResearchCandidateRelation.UNCLASSIFIED
                rationale = "structured_adjudicators_disagree_with_each_other_or_semantics"
                method = CandidateClassificationMethod.ADJUDICATOR_DISAGREEMENT
                confidence = min(item.confidence for item in admissible_judgments)
            else:
                relation = next(iter(judged_relations))
                rationale = "structured_adjudicators_reached_bound_consensus"
                confidence = sum(item.confidence for item in admissible_judgments) / len(
                    admissible_judgments
                )
                method = (
                    CandidateClassificationMethod.DETERMINISTIC_STRUCTURED_CONSENSUS
                    if semantic.relation
                    not in {
                        ConservativeSemanticRelation.ambiguity,
                        ConservativeSemanticRelation.insufficiency,
                        ConservativeSemanticRelation.irrelevance,
                    }
                    else CandidateClassificationMethod.STRUCTURED_CONSENSUS
                )
        material = relation is not ResearchCandidateRelation.IRRELEVANT and (
            relation
            in {
                ResearchCandidateRelation.AMBIGUOUS,
                ResearchCandidateRelation.UNCLASSIFIED,
            }
            or confidence >= self.policy.material_minimum_confidence
        )
        payload = {
            "schema_version": "bijux.canon.reason.candidate_classification.v1",
            "requirement_artifact_id": requirement_artifact_id,
            "claim_artifact_id": claim_artifact_id,
            "evidence_artifact_id": candidate.artifact_id,
            "locator_artifact_id": candidate.locator.artifact_id,
            "exact_text_sha256": candidate.exact_text_sha256,
            "relation": relation.value,
            "rationale": rationale,
            "method": method.value,
            "confidence": confidence,
            "material": material,
            "semantic_coverage": semantic.claim_term_coverage,
            "judgment_artifact_ids": tuple(item.artifact_id for item in judgments),
        }
        return ResearchCandidateClassification(
            artifact_id=content_artifact_id(payload),
            requirement_artifact_id=requirement_artifact_id,
            claim_artifact_id=claim_artifact_id,
            evidence_artifact_id=candidate.artifact_id,
            locator_artifact_id=candidate.locator.artifact_id,
            exact_text_sha256=candidate.exact_text_sha256,
            relation=relation,
            rationale=rationale,
            method=method,
            confidence=confidence,
            material=material,
            semantic_coverage=semantic.claim_term_coverage,
            judgment_artifact_ids=tuple(item.artifact_id for item in judgments),
        )


def _semantic_relation(
    relation: ConservativeSemanticRelation,
    *,
    requirement_kind: str,
    evidence_text: str,
    coverage: float,
    related_threshold: float,
) -> ResearchCandidateRelation:
    if (
        requirement_kind == "limitation"
        and coverage >= related_threshold
        and _LIMITATION.search(evidence_text)
    ):
        return ResearchCandidateRelation.LIMITING
    return {
        ConservativeSemanticRelation.direct_support: ResearchCandidateRelation.SUPPORTING,
        ConservativeSemanticRelation.opposition: ResearchCandidateRelation.OPPOSING,
        ConservativeSemanticRelation.ambiguity: ResearchCandidateRelation.AMBIGUOUS,
        ConservativeSemanticRelation.irrelevance: ResearchCandidateRelation.IRRELEVANT,
        ConservativeSemanticRelation.insufficiency: ResearchCandidateRelation.UNCLASSIFIED,
    }[relation]


__all__ = [
    "CandidateAdjudicationPolicy",
    "CandidateAdjudicationReport",
    "CandidateClassificationMethod",
    "DuplicateResearchCandidate",
    "ResearchCandidateAdjudicationService",
    "ResearchCandidateClassification",
    "ResearchCandidateRelation",
    "StructuredCandidateJudgment",
]
