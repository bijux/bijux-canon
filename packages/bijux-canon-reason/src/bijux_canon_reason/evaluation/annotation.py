# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Source-first annotation revision, review, and adjudication workflow."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.evaluation.truth import (
    EvaluationCaseTruth,
    EvaluationSplit,
    Identifier,
    NonEmptyText,
    Sha256,
)


class AnnotationReviewVerdict(StrEnum):
    """Independent review decision for one truth revision."""

    approve = "approve"
    changes_required = "changes_required"


class AnnotationAdjudicationVerdict(StrEnum):
    """Final adjudication decision when independent reviews disagree."""

    admit = "admit"
    reject = "reject"


class AnnotationProtocol(StableModel):
    """Immutable identity of the human annotation instructions in force."""

    schema_version: Literal["bijux.canon.evaluation.annotation-protocol.v1"] = (
        "bijux.canon.evaluation.annotation-protocol.v1"
    )
    protocol_id: Identifier
    revision: int = Field(ge=1)
    guidelines_sha256: Sha256
    minimum_heldout_reviewers: int = Field(default=2, ge=2)
    source_first: Literal[True] = True
    system_output_labels_prohibited: Literal[True] = True


class AnnotationRevision(StableModel):
    """One immutable truth revision linked to its immediate predecessor."""

    schema_version: Literal["bijux.canon.evaluation.annotation-revision.v1"] = (
        "bijux.canon.evaluation.annotation-revision.v1"
    )
    revision_id: Identifier
    case: EvaluationCaseTruth
    protocol_sha256: Sha256
    parent_revision_sha256: Sha256 | None = None
    authored_by: Identifier
    authored_on: date
    source_material_reviewed: Literal[True] = True
    system_output_consulted: Literal[False] = False

    @property
    def identity_sha256(self) -> str:
        """Return the canonical content identity of this frozen revision."""
        return _identity(self)


class AnnotationConflict(StableModel):
    """A concrete disagreement that must remain visible until adjudication."""

    schema_version: Literal["bijux.canon.evaluation.annotation-conflict.v1"] = (
        "bijux.canon.evaluation.annotation-conflict.v1"
    )
    conflict_id: Identifier
    subject_id: Identifier
    description: NonEmptyText


class AnnotationReview(StableModel):
    """One source-first review of an exact annotation revision."""

    schema_version: Literal["bijux.canon.evaluation.annotation-review.v1"] = (
        "bijux.canon.evaluation.annotation-review.v1"
    )
    review_id: Identifier
    revision_sha256: Sha256
    protocol_sha256: Sha256
    reviewer_id: Identifier
    reviewed_on: date
    verdict: AnnotationReviewVerdict
    rationale: NonEmptyText
    conflicts: tuple[AnnotationConflict, ...] = ()
    source_material_reviewed: Literal[True] = True
    system_output_consulted: Literal[False] = False

    @model_validator(mode="after")
    def _validate_conflicts(self) -> AnnotationReview:
        conflict_ids = [conflict.conflict_id for conflict in self.conflicts]
        if len(set(conflict_ids)) != len(conflict_ids):
            raise ValueError("annotation review conflict IDs must be unique")
        if self.verdict is AnnotationReviewVerdict.approve and self.conflicts:
            raise ValueError("an approving annotation review cannot retain conflicts")
        return self


class AnnotationAdjudication(StableModel):
    """Resolution of disagreeing independent annotation reviews."""

    schema_version: Literal["bijux.canon.evaluation.annotation-adjudication.v1"] = (
        "bijux.canon.evaluation.annotation-adjudication.v1"
    )
    adjudication_id: Identifier
    revision_sha256: Sha256
    protocol_sha256: Sha256
    review_ids: tuple[Identifier, ...] = Field(min_length=2)
    adjudicator_id: Identifier
    adjudicated_on: date
    verdict: AnnotationAdjudicationVerdict
    resolved_conflict_ids: tuple[Identifier, ...] = ()
    rationale: NonEmptyText
    source_material_reviewed: Literal[True] = True
    system_output_consulted: Literal[False] = False

    @model_validator(mode="after")
    def _validate_references(self) -> AnnotationAdjudication:
        if len(set(self.review_ids)) != len(self.review_ids):
            raise ValueError("annotation adjudication review IDs must be unique")
        if len(set(self.resolved_conflict_ids)) != len(self.resolved_conflict_ids):
            raise ValueError("resolved annotation conflict IDs must be unique")
        return self


class AnnotationAdmission(StableModel):
    """Immutable outcome proving that one truth revision passed review policy."""

    schema_version: Literal["bijux.canon.evaluation.annotation-admission.v1"] = (
        "bijux.canon.evaluation.annotation-admission.v1"
    )
    case_id: Identifier
    split: EvaluationSplit
    revision_sha256: Sha256
    protocol_sha256: Sha256
    review_ids: tuple[Identifier, ...] = Field(min_length=1)
    reviewer_ids: tuple[Identifier, ...] = Field(min_length=1)
    adjudication_id: Identifier | None
    resolved_conflict_ids: tuple[Identifier, ...]

    @model_validator(mode="after")
    def _validate_identifiers(self) -> AnnotationAdmission:
        if len(set(self.review_ids)) != len(self.review_ids):
            raise ValueError("annotation admission review IDs must be unique")
        if len(set(self.reviewer_ids)) != len(self.reviewer_ids):
            raise ValueError("annotation admission reviewer IDs must be unique")
        if len(self.review_ids) != len(self.reviewer_ids):
            raise ValueError("annotation admission review lineage is incomplete")
        if len(set(self.resolved_conflict_ids)) != len(self.resolved_conflict_ids):
            raise ValueError("annotation admission conflict IDs must be unique")
        return self

    @property
    def identity_sha256(self) -> str:
        """Return the canonical content identity of this frozen admission."""
        return _identity(self)


class AnnotationWorkflowError(ValueError):
    """Annotation history cannot be admitted under the bound protocol."""


class IndependentAnnotationWorkflow:
    """Validate source-first revision lineage and independent human decisions."""

    def __init__(self, protocol: AnnotationProtocol) -> None:
        self._protocol = protocol

    def admit(
        self,
        *,
        revisions: tuple[AnnotationRevision, ...],
        reviews: tuple[AnnotationReview, ...],
        adjudication: AnnotationAdjudication | None = None,
    ) -> AnnotationAdmission:
        """Admit the latest immutable revision when independent review is complete."""
        selected = self._validate_revision_lineage(revisions)
        selected_reviews = self._validate_reviews(selected, reviews)
        conflicts = {
            conflict.conflict_id
            for review in selected_reviews
            for conflict in review.conflicts
        }
        requires_adjudication = bool(conflicts) or any(
            review.verdict is AnnotationReviewVerdict.changes_required
            for review in selected_reviews
        )
        self._validate_review_count(selected, selected_reviews)
        resolved = self._validate_adjudication(
            selected,
            selected_reviews,
            conflicts,
            adjudication,
            required=requires_adjudication,
        )
        return AnnotationAdmission(
            case_id=selected.case.case_id,
            split=selected.case.split,
            revision_sha256=selected.identity_sha256,
            protocol_sha256=self._protocol.guidelines_sha256,
            review_ids=tuple(sorted(review.review_id for review in selected_reviews)),
            reviewer_ids=tuple(
                sorted(review.reviewer_id for review in selected_reviews)
            ),
            adjudication_id=(
                None if adjudication is None else adjudication.adjudication_id
            ),
            resolved_conflict_ids=tuple(sorted(resolved)),
        )

    def _validate_revision_lineage(
        self,
        revisions: tuple[AnnotationRevision, ...],
    ) -> AnnotationRevision:
        if not revisions:
            raise AnnotationWorkflowError("annotation history must contain a revision")
        case_id = revisions[0].case.case_id
        seen_ids: set[str] = set()
        parent: str | None = None
        for revision in revisions:
            if revision.revision_id in seen_ids:
                raise AnnotationWorkflowError("annotation revision IDs must be unique")
            seen_ids.add(revision.revision_id)
            if revision.case.case_id != case_id:
                raise AnnotationWorkflowError(
                    "annotation revisions must belong to one case"
                )
            if revision.protocol_sha256 != self._protocol.guidelines_sha256:
                raise AnnotationWorkflowError(
                    "annotation revision uses another protocol identity"
                )
            if revision.parent_revision_sha256 != parent:
                raise AnnotationWorkflowError("annotation revision lineage is broken")
            parent = revision.identity_sha256
        return revisions[-1]

    def _validate_reviews(
        self,
        selected: AnnotationRevision,
        reviews: tuple[AnnotationReview, ...],
    ) -> tuple[AnnotationReview, ...]:
        if not reviews:
            raise AnnotationWorkflowError(
                "annotation revision has no independent reviews"
            )
        revision_sha256 = selected.identity_sha256
        review_ids: set[str] = set()
        reviewer_ids: set[str] = set()
        for review in reviews:
            if review.review_id in review_ids:
                raise AnnotationWorkflowError("annotation review IDs must be unique")
            if review.reviewer_id in reviewer_ids:
                raise AnnotationWorkflowError(
                    "each annotation review requires a distinct reviewer"
                )
            if review.reviewer_id == selected.authored_by:
                raise AnnotationWorkflowError(
                    "annotation authors cannot review their own revision"
                )
            if review.revision_sha256 != revision_sha256:
                raise AnnotationWorkflowError(
                    "annotation review targets another revision"
                )
            if review.protocol_sha256 != self._protocol.guidelines_sha256:
                raise AnnotationWorkflowError(
                    "annotation review uses another protocol identity"
                )
            review_ids.add(review.review_id)
            reviewer_ids.add(review.reviewer_id)
        return reviews

    def _validate_review_count(
        self,
        selected: AnnotationRevision,
        reviews: tuple[AnnotationReview, ...],
    ) -> None:
        if selected.case.split is not EvaluationSplit.heldout:
            return
        required = self._protocol.minimum_heldout_reviewers
        if len(reviews) < required:
            raise AnnotationWorkflowError(
                f"held-out annotation requires at least {required} independent reviews"
            )

    def _validate_adjudication(
        self,
        selected: AnnotationRevision,
        reviews: tuple[AnnotationReview, ...],
        conflicts: set[str],
        adjudication: AnnotationAdjudication | None,
        *,
        required: bool,
    ) -> set[str]:
        if adjudication is None:
            if required:
                raise AnnotationWorkflowError(
                    "review disagreement requires explicit adjudication"
                )
            return set()
        if adjudication.revision_sha256 != selected.identity_sha256:
            raise AnnotationWorkflowError("adjudication targets another revision")
        if adjudication.protocol_sha256 != self._protocol.guidelines_sha256:
            raise AnnotationWorkflowError("adjudication uses another protocol identity")
        if set(adjudication.review_ids) != {review.review_id for review in reviews}:
            raise AnnotationWorkflowError(
                "adjudication must reference every selected independent review"
            )
        if adjudication.adjudicator_id in {review.reviewer_id for review in reviews}:
            raise AnnotationWorkflowError(
                "annotation adjudicator must be independent of the reviewers"
            )
        if set(adjudication.resolved_conflict_ids) != conflicts:
            raise AnnotationWorkflowError(
                "adjudication must resolve the exact recorded conflict set"
            )
        if adjudication.verdict is not AnnotationAdjudicationVerdict.admit:
            raise AnnotationWorkflowError(
                "annotation adjudication rejected the revision"
            )
        return conflicts


def _identity(model: StableModel) -> str:
    payload = json.dumps(
        model.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


__all__ = [
    "AnnotationAdjudication",
    "AnnotationAdjudicationVerdict",
    "AnnotationAdmission",
    "AnnotationConflict",
    "AnnotationProtocol",
    "AnnotationReview",
    "AnnotationReviewVerdict",
    "AnnotationRevision",
    "AnnotationWorkflowError",
    "IndependentAnnotationWorkflow",
]
