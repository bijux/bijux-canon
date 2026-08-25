# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Qualifier-aware independent review of emitted claims against frozen truth."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.evaluation.outcomes import SystemOutput
from bijux_canon_reason.evaluation.truth import (
    EvaluationCaseTruth,
    Identifier,
    NonEmptyText,
)
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)


class ClaimMatchRelation(StrEnum):
    """Reviewed semantic relationship between emitted and truth claims."""

    equivalent = "equivalent"
    qualified_equivalent = "qualified_equivalent"
    overgeneralized = "overgeneralized"
    contradicts = "contradicts"
    unrelated = "unrelated"
    ambiguous = "ambiguous"


class ClaimQualifierAlignment(StableModel):
    """Material proposition dimensions retained by an emitted claim."""

    entity: bool
    scope: bool
    quantity: bool
    modality: bool
    negation: bool

    @property
    def complete(self) -> bool:
        """Return whether every material qualifier survived."""

        return all(
            (self.entity, self.scope, self.quantity, self.modality, self.negation)
        )


class ClaimMatchReview(StableModel):
    """One output-aware review that cannot alter independently frozen truth."""

    schema_version: Literal["bijux.canon.evaluation.claim-match-review.v1"] = (
        "bijux.canon.evaluation.claim-match-review.v1"
    )
    artifact_id: str
    case_id: Identifier
    system_output_id: Identifier
    system_claim_id: Identifier
    truth_claim_id: Identifier | None
    relation: ClaimMatchRelation
    qualifier_alignment: ClaimQualifierAlignment
    reviewed_qrel_ids: tuple[Identifier, ...]
    reviewer_id: Identifier
    reviewed_on: date
    rationale: NonEmptyText
    truth_artifact_id: str
    system_output_artifact_id: str
    independent_of_system_generation: Literal[True] = True

    @field_validator("artifact_id", "truth_artifact_id", "system_output_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_review(self) -> Self:
        if len(set(self.reviewed_qrel_ids)) != len(self.reviewed_qrel_ids):
            raise ValueError("claim-match reviewed qrel IDs must be unique")
        if self.truth_claim_id is None and self.relation not in {
            ClaimMatchRelation.unrelated,
            ClaimMatchRelation.ambiguous,
        }:
            raise ValueError("a semantic match requires a reviewed truth claim")
        if self.truth_claim_id is None and self.reviewed_qrel_ids:
            raise ValueError("an unmatched claim cannot inherit reviewed qrels")
        if (
            self.relation
            in {
                ClaimMatchRelation.equivalent,
                ClaimMatchRelation.qualified_equivalent,
            }
            and not self.qualifier_alignment.complete
        ):
            raise ValueError("equivalent claims must retain every material qualifier")
        if (
            self.relation is ClaimMatchRelation.overgeneralized
            and self.qualifier_alignment.complete
        ):
            raise ValueError("overgeneralization must identify a lost qualifier")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("claim-match review identity does not match")
        return self


class ClaimMatchAdjudication(StableModel):
    """Resolution of disagreeing reviews while retaining every decision."""

    schema_version: Literal["bijux.canon.evaluation.claim-match-adjudication.v1"] = (
        "bijux.canon.evaluation.claim-match-adjudication.v1"
    )
    artifact_id: str
    case_id: Identifier
    system_output_id: Identifier
    system_claim_id: Identifier
    review_artifact_ids: tuple[str, ...] = Field(min_length=2)
    truth_claim_id: Identifier | None
    relation: ClaimMatchRelation
    qualifier_alignment: ClaimQualifierAlignment
    reviewed_qrel_ids: tuple[Identifier, ...]
    adjudicator_id: Identifier
    adjudicated_on: date
    rationale: NonEmptyText

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("review_artifact_ids")
    @classmethod
    def _validate_review_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("claim-match adjudication review IDs must be unique")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_adjudication(self) -> Self:
        if len(set(self.reviewed_qrel_ids)) != len(self.reviewed_qrel_ids):
            raise ValueError("adjudicated qrel IDs must be unique")
        if self.truth_claim_id is None and self.relation not in {
            ClaimMatchRelation.unrelated,
            ClaimMatchRelation.ambiguous,
        }:
            raise ValueError("an adjudicated semantic match requires truth")
        if self.truth_claim_id is None and self.reviewed_qrel_ids:
            raise ValueError("an unmatched adjudication cannot inherit qrels")
        if (
            self.relation
            in {
                ClaimMatchRelation.equivalent,
                ClaimMatchRelation.qualified_equivalent,
            }
            and not self.qualifier_alignment.complete
        ):
            raise ValueError("adjudicated equivalence must retain every qualifier")
        if (
            self.relation is ClaimMatchRelation.overgeneralized
            and self.qualifier_alignment.complete
        ):
            raise ValueError("adjudicated overgeneralization must lose a qualifier")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("claim-match adjudication identity does not match")
        return self


class ClaimMatchOutcome(StableModel):
    """Effective semantic match for one emitted atomic claim."""

    system_claim_id: Identifier
    truth_claim_id: Identifier | None
    relation: ClaimMatchRelation
    qualifier_alignment: ClaimQualifierAlignment
    reviewed_qrel_ids: tuple[Identifier, ...]
    review_artifact_ids: tuple[str, ...]
    adjudication_artifact_id: str | None
    reviewer_disagreement: bool
    unresolved: bool
    rationale: NonEmptyText

    @property
    def admitted_equivalence(self) -> bool:
        """Return whether the emitted claim is a qualifier-complete paraphrase."""

        return (
            not self.unresolved
            and self.truth_claim_id is not None
            and self.qualifier_alignment.complete
            and self.relation
            in {
                ClaimMatchRelation.equivalent,
                ClaimMatchRelation.qualified_equivalent,
            }
        )


class ClaimMatchErrorKind(StrEnum):
    """Representative semantic error classes retained in reports."""

    overgeneralized = "overgeneralized"
    contradicts = "contradicts"
    unrelated = "unrelated"
    ambiguous = "ambiguous"
    reviewer_disagreement = "reviewer_disagreement"


class ClaimMatchError(StableModel):
    """One emitted claim that did not earn qualifier-complete match credit."""

    kind: ClaimMatchErrorKind
    system_claim_id: Identifier
    truth_claim_id: Identifier | None
    detail: NonEmptyText


class ClaimMatchReport(StableModel):
    """Content-addressed semantic review, adjudication, and error analysis."""

    schema_version: Literal["bijux.canon.evaluation.claim-match-report.v1"] = (
        "bijux.canon.evaluation.claim-match-report.v1"
    )
    artifact_id: str
    case_id: Identifier
    system_output_id: Identifier
    truth_artifact_id: str
    system_output_artifact_id: str
    reviews: tuple[ClaimMatchReview, ...]
    adjudications: tuple[ClaimMatchAdjudication, ...]
    outcomes: tuple[ClaimMatchOutcome, ...]
    errors: tuple[ClaimMatchError, ...]

    @field_validator("artifact_id", "truth_artifact_id", "system_output_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_report(self) -> Self:
        if len({item.system_claim_id for item in self.outcomes}) != len(self.outcomes):
            raise ValueError("claim-match outcomes must be unique")
        if len({item.artifact_id for item in self.reviews}) != len(self.reviews):
            raise ValueError("claim-match reviews must be unique")
        if len({item.artifact_id for item in self.adjudications}) != len(
            self.adjudications
        ):
            raise ValueError("claim-match adjudications must be unique")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("claim-match report identity does not match")
        return self


class ClaimMatchEvaluationError(ValueError):
    """Claim reviews do not completely and coherently cover one output."""


class ClaimMatchEvaluator:
    """Resolve independent semantic reviews without inspecting answer keywords."""

    def evaluate(
        self,
        *,
        case: EvaluationCaseTruth,
        output: SystemOutput,
        reviews: tuple[ClaimMatchReview, ...],
        adjudications: tuple[ClaimMatchAdjudication, ...] = (),
    ) -> ClaimMatchReport:
        """Return one effective match per emitted claim and retain disagreements."""

        reviews = tuple(
            sorted(
                reviews,
                key=lambda item: (
                    item.system_claim_id,
                    item.reviewer_id,
                    item.artifact_id,
                ),
            )
        )
        adjudications = tuple(
            sorted(adjudications, key=lambda item: item.system_claim_id)
        )
        truth_artifact_id = content_artifact_id(case.model_dump(mode="json"))
        output_artifact_id = content_artifact_id(output.model_dump(mode="json"))
        self._validate_bindings(
            case,
            output,
            reviews,
            adjudications,
            truth_artifact_id,
            output_artifact_id,
        )
        by_claim = {
            claim.claim_id: tuple(
                item for item in reviews if item.system_claim_id == claim.claim_id
            )
            for claim in output.claims
        }
        adjudication_by_claim = {item.system_claim_id: item for item in adjudications}
        outcomes = tuple(
            self._resolve(
                claim_id,
                by_claim[claim_id],
                adjudication_by_claim.get(claim_id),
            )
            for claim_id in sorted(by_claim)
        )
        errors = tuple(
            _error(item)
            for item in outcomes
            if not item.admitted_equivalence or item.reviewer_disagreement
        )
        payload = {
            "schema_version": "bijux.canon.evaluation.claim-match-report.v1",
            "case_id": case.case_id,
            "system_output_id": output.output_id,
            "truth_artifact_id": truth_artifact_id,
            "system_output_artifact_id": output_artifact_id,
            "reviews": tuple(item.model_dump(mode="json") for item in reviews),
            "adjudications": tuple(
                item.model_dump(mode="json") for item in adjudications
            ),
            "outcomes": tuple(item.model_dump(mode="json") for item in outcomes),
            "errors": tuple(item.model_dump(mode="json") for item in errors),
        }
        return ClaimMatchReport.model_validate(
            {"artifact_id": content_artifact_id(payload), **payload}
        )

    @staticmethod
    def _validate_bindings(
        case: EvaluationCaseTruth,
        output: SystemOutput,
        reviews: tuple[ClaimMatchReview, ...],
        adjudications: tuple[ClaimMatchAdjudication, ...],
        truth_artifact_id: str,
        output_artifact_id: str,
    ) -> None:
        if case.case_id != output.case_id:
            raise ClaimMatchEvaluationError("claim-match case and output differ")
        claim_ids = {item.claim_id for item in output.claims}
        truth_by_id = {item.claim_truth_id: item for item in case.claims}
        review_claim_ids = {item.system_claim_id for item in reviews}
        if review_claim_ids != claim_ids:
            raise ClaimMatchEvaluationError(
                "claim-match reviews must cover every emitted claim exactly"
            )
        for review in reviews:
            if (
                review.case_id != case.case_id
                or review.system_output_id != output.output_id
                or review.truth_artifact_id != truth_artifact_id
                or review.system_output_artifact_id != output_artifact_id
            ):
                raise ClaimMatchEvaluationError("claim-match review binding differs")
            truth = (
                None
                if review.truth_claim_id is None
                else truth_by_id.get(review.truth_claim_id)
            )
            if review.truth_claim_id is not None and truth is None:
                raise ClaimMatchEvaluationError(
                    "claim-match review names unknown truth"
                )
            allowed_qrels = (
                set() if truth is None else {item.qrel_id for item in truth.citations}
            )
            if not set(review.reviewed_qrel_ids).issubset(allowed_qrels):
                raise ClaimMatchEvaluationError(
                    "claim-match review names unrelated qrels"
                )
        grouped_reviewers: dict[str, set[str]] = {}
        for review in reviews:
            reviewers = grouped_reviewers.setdefault(review.system_claim_id, set())
            if review.reviewer_id in reviewers:
                raise ClaimMatchEvaluationError(
                    "one reviewer cannot decide an emitted claim twice"
                )
            reviewers.add(review.reviewer_id)
        adjudication_claim_ids = [item.system_claim_id for item in adjudications]
        if len(set(adjudication_claim_ids)) != len(adjudication_claim_ids):
            raise ClaimMatchEvaluationError("claim-match adjudications must be unique")
        if not set(adjudication_claim_ids).issubset(claim_ids):
            raise ClaimMatchEvaluationError(
                "claim-match adjudication names unknown claim"
            )
        for adjudication in adjudications:
            if (
                adjudication.case_id != case.case_id
                or adjudication.system_output_id != output.output_id
            ):
                raise ClaimMatchEvaluationError(
                    "claim-match adjudication binding differs"
                )
            truth = (
                None
                if adjudication.truth_claim_id is None
                else truth_by_id.get(adjudication.truth_claim_id)
            )
            if adjudication.truth_claim_id is not None and truth is None:
                raise ClaimMatchEvaluationError(
                    "claim-match adjudication names unknown truth"
                )
            allowed_qrels = (
                set() if truth is None else {item.qrel_id for item in truth.citations}
            )
            if not set(adjudication.reviewed_qrel_ids).issubset(allowed_qrels):
                raise ClaimMatchEvaluationError(
                    "claim-match adjudication names unrelated qrels"
                )

    @staticmethod
    def _resolve(
        claim_id: str,
        reviews: tuple[ClaimMatchReview, ...],
        adjudication: ClaimMatchAdjudication | None,
    ) -> ClaimMatchOutcome:
        signatures = {_signature(item) for item in reviews}
        disagreement = len(signatures) > 1
        if not disagreement:
            if adjudication is not None:
                raise ClaimMatchEvaluationError(
                    "agreeing reviews cannot be overwritten by adjudication"
                )
            selected = reviews[0]
            return ClaimMatchOutcome(
                system_claim_id=claim_id,
                truth_claim_id=selected.truth_claim_id,
                relation=selected.relation,
                qualifier_alignment=selected.qualifier_alignment,
                reviewed_qrel_ids=selected.reviewed_qrel_ids,
                review_artifact_ids=tuple(item.artifact_id for item in reviews),
                adjudication_artifact_id=None,
                reviewer_disagreement=False,
                unresolved=False,
                rationale=selected.rationale,
            )
        if adjudication is None:
            return ClaimMatchOutcome(
                system_claim_id=claim_id,
                truth_claim_id=None,
                relation=ClaimMatchRelation.ambiguous,
                qualifier_alignment=ClaimQualifierAlignment(
                    entity=False,
                    scope=False,
                    quantity=False,
                    modality=False,
                    negation=False,
                ),
                reviewed_qrel_ids=(),
                review_artifact_ids=tuple(item.artifact_id for item in reviews),
                adjudication_artifact_id=None,
                reviewer_disagreement=True,
                unresolved=True,
                rationale="independent reviewers disagree and no adjudication resolves the match",
            )
        review_ids = tuple(item.artifact_id for item in reviews)
        if (
            adjudication.case_id != reviews[0].case_id
            or adjudication.system_output_id != reviews[0].system_output_id
            or adjudication.system_claim_id != claim_id
            or set(adjudication.review_artifact_ids) != set(review_ids)
            or adjudication.adjudicator_id in {item.reviewer_id for item in reviews}
        ):
            raise ClaimMatchEvaluationError("claim-match adjudication lineage differs")
        return ClaimMatchOutcome(
            system_claim_id=claim_id,
            truth_claim_id=adjudication.truth_claim_id,
            relation=adjudication.relation,
            qualifier_alignment=adjudication.qualifier_alignment,
            reviewed_qrel_ids=adjudication.reviewed_qrel_ids,
            review_artifact_ids=review_ids,
            adjudication_artifact_id=adjudication.artifact_id,
            reviewer_disagreement=True,
            unresolved=False,
            rationale=adjudication.rationale,
        )


def _signature(
    review: ClaimMatchReview,
) -> tuple[str | None, ClaimMatchRelation, tuple[bool, ...], tuple[str, ...]]:
    alignment = review.qualifier_alignment
    return (
        review.truth_claim_id,
        review.relation,
        (
            alignment.entity,
            alignment.scope,
            alignment.quantity,
            alignment.modality,
            alignment.negation,
        ),
        review.reviewed_qrel_ids,
    )


def _error(outcome: ClaimMatchOutcome) -> ClaimMatchError:
    if outcome.reviewer_disagreement:
        kind = ClaimMatchErrorKind.reviewer_disagreement
    else:
        kind = ClaimMatchErrorKind(outcome.relation.value)
    return ClaimMatchError(
        kind=kind,
        system_claim_id=outcome.system_claim_id,
        truth_claim_id=outcome.truth_claim_id,
        detail=outcome.rationale,
    )


def create_claim_match_review(
    *,
    case: EvaluationCaseTruth,
    output: SystemOutput,
    system_claim_id: str,
    truth_claim_id: str | None,
    relation: ClaimMatchRelation,
    qualifier_alignment: ClaimQualifierAlignment,
    reviewed_qrel_ids: tuple[str, ...],
    reviewer_id: str,
    reviewed_on: date,
    rationale: str,
) -> ClaimMatchReview:
    """Create one immutable review bound to exact truth and system output bytes."""

    payload = {
        "schema_version": "bijux.canon.evaluation.claim-match-review.v1",
        "case_id": case.case_id,
        "system_output_id": output.output_id,
        "system_claim_id": system_claim_id,
        "truth_claim_id": truth_claim_id,
        "relation": relation.value,
        "qualifier_alignment": qualifier_alignment.model_dump(mode="json"),
        "reviewed_qrel_ids": reviewed_qrel_ids,
        "reviewer_id": reviewer_id,
        "reviewed_on": reviewed_on.isoformat(),
        "rationale": rationale,
        "truth_artifact_id": content_artifact_id(case.model_dump(mode="json")),
        "system_output_artifact_id": content_artifact_id(
            output.model_dump(mode="json")
        ),
        "independent_of_system_generation": True,
    }
    return ClaimMatchReview.model_validate(
        {"artifact_id": content_artifact_id(payload), **payload}
    )


def create_claim_match_adjudication(
    *,
    reviews: tuple[ClaimMatchReview, ...],
    truth_claim_id: str | None,
    relation: ClaimMatchRelation,
    qualifier_alignment: ClaimQualifierAlignment,
    reviewed_qrel_ids: tuple[str, ...],
    adjudicator_id: str,
    adjudicated_on: date,
    rationale: str,
) -> ClaimMatchAdjudication:
    """Create an immutable resolution over exact disagreeing review artifacts."""

    if len(reviews) < 2:
        raise ClaimMatchEvaluationError("adjudication requires at least two reviews")
    first = reviews[0]
    if any(
        item.case_id != first.case_id
        or item.system_output_id != first.system_output_id
        or item.system_claim_id != first.system_claim_id
        for item in reviews
    ):
        raise ClaimMatchEvaluationError("adjudicated reviews describe different claims")
    payload = {
        "schema_version": "bijux.canon.evaluation.claim-match-adjudication.v1",
        "case_id": first.case_id,
        "system_output_id": first.system_output_id,
        "system_claim_id": first.system_claim_id,
        "review_artifact_ids": tuple(item.artifact_id for item in reviews),
        "truth_claim_id": truth_claim_id,
        "relation": relation.value,
        "qualifier_alignment": qualifier_alignment.model_dump(mode="json"),
        "reviewed_qrel_ids": reviewed_qrel_ids,
        "adjudicator_id": adjudicator_id,
        "adjudicated_on": adjudicated_on.isoformat(),
        "rationale": rationale,
    }
    return ClaimMatchAdjudication.model_validate(
        {"artifact_id": content_artifact_id(payload), **payload}
    )


__all__ = [
    "ClaimMatchAdjudication",
    "ClaimMatchError",
    "ClaimMatchErrorKind",
    "ClaimMatchEvaluationError",
    "ClaimMatchEvaluator",
    "ClaimMatchOutcome",
    "ClaimMatchRelation",
    "ClaimMatchReport",
    "ClaimMatchReview",
    "ClaimQualifierAlignment",
    "create_claim_match_adjudication",
    "create_claim_match_review",
]
