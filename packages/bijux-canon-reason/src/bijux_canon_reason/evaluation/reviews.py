# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Independent review and adjudication records for evaluation outputs."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.evaluation.truth import Identifier, NonEmptyText, Sha256


class ReviewSubjectKind(StrEnum):
    """Kinds of system-output surface that can be reviewed."""

    answer = "answer"
    retrieval = "retrieval"
    claim = "claim"
    citation = "citation"
    conflict = "conflict"
    abstention = "abstention"
    policy = "policy"


class ReviewVerdict(StrEnum):
    """Reviewer decision for one evaluation subject."""

    pass_ = "pass"
    fail = "fail"
    insufficient = "insufficient"
    excluded = "excluded"


class ReviewerDecision(StableModel):
    """One independently authored reviewer decision."""

    schema_version: Literal["bijux.canon.evaluation.reviewer-decision.v1"] = (
        "bijux.canon.evaluation.reviewer-decision.v1"
    )
    decision_id: Identifier
    case_id: Identifier
    system_output_id: Identifier
    reviewer_id: Identifier
    reviewed_on: date
    subject_kind: ReviewSubjectKind
    subject_id: Identifier
    verdict: ReviewVerdict
    label: Identifier
    rationale: NonEmptyText
    truth_identity_sha256: Sha256
    system_output_identity_sha256: Sha256
    independent_of_system_generation: Literal[True] = True


class AdjudicationDecision(StableModel):
    """Resolution of multiple independent reviewer decisions."""

    schema_version: Literal["bijux.canon.evaluation.adjudication.v1"] = (
        "bijux.canon.evaluation.adjudication.v1"
    )
    adjudication_id: Identifier
    case_id: Identifier
    system_output_id: Identifier
    reviewer_decision_ids: tuple[Identifier, ...] = Field(min_length=2)
    adjudicator_id: Identifier
    adjudicated_on: date
    verdict: ReviewVerdict
    rationale: NonEmptyText

    @model_validator(mode="after")
    def _require_distinct_decisions(self) -> AdjudicationDecision:
        if len(set(self.reviewer_decision_ids)) != len(self.reviewer_decision_ids):
            raise ValueError("adjudication reviewer decision IDs must be unique")
        return self


__all__ = [
    "AdjudicationDecision",
    "ReviewerDecision",
    "ReviewSubjectKind",
    "ReviewVerdict",
]
