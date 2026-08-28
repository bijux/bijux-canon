# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Tests for source-first independent evaluation annotation."""

from __future__ import annotations

from datetime import date
import hashlib
from pathlib import Path

from pydantic import ValidationError
import pytest

from bijux_canon_reason.evaluation import (
    AbstentionExpectation,
    AnnotationAdjudication,
    AnnotationAdjudicationVerdict,
    AnnotationConflict,
    AnnotationProtocol,
    AnnotationReview,
    AnnotationReviewVerdict,
    AnnotationRevision,
    AnnotationWorkflowError,
    AtomicClaimTruth,
    CitationTruthLabel,
    CitationTruthRelation,
    ClaimTruthClass,
    ConflictExpectation,
    EvaluationCaseTruth,
    EvaluationQuery,
    EvaluationSplit,
    ExactEvidenceLocator,
    IndependentAnnotationWorkflow,
    QrelJudgment,
    TruthProvenance,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
PROTOCOL_PATH = REPO_ROOT / "docs/04-bijux-canon-reason/quality/annotation-protocol.md"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _protocol() -> AnnotationProtocol:
    return AnnotationProtocol(
        protocol_id="independent-source-first",
        revision=1,
        guidelines_sha256=hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest(),
    )


def _case(split: EvaluationSplit) -> EvaluationCaseTruth:
    exact_text = "Ancient genomes preserve direct population evidence."
    provenance = TruthProvenance(
        reviewer_ids=("truth-author",),
        reviewed_on=date(2026, 8, 22),
        review_method="Source-first exact-span annotation.",
        source_identity_sha256="a" * 64,
        data_identity_sha256="b" * 64,
    )
    locator = ExactEvidenceLocator(
        locator_id="source-1:span-1",
        source_id="source-1",
        source_uri="corpus://source-1",
        source_sha256="a" * 64,
        chunk_id="chunk-1",
        character_start=0,
        character_end=len(exact_text),
        exact_text=exact_text,
        exact_text_sha256=_sha256(exact_text),
    )
    qrel = QrelJudgment(
        qrel_id="qrel-1",
        query_id="query-1",
        relevance_grade=3,
        locator=locator,
        rationale="The span directly answers the source-grounded question.",
        provenance=provenance,
    )
    citation = CitationTruthLabel(
        citation_label_id="citation-label-1",
        qrel_id=qrel.qrel_id,
        relation=CitationTruthRelation.supports,
        rationale="The exact span directly supports the atomic claim.",
        provenance=provenance,
    )
    claim = AtomicClaimTruth(
        claim_truth_id="claim-1",
        query_id="query-1",
        statement=exact_text,
        claim_class=ClaimTruthClass.expected,
        expected_in_answer=True,
        abstention_expectation=AbstentionExpectation.prohibited,
        citations=(citation,),
        rationale="The admitted source states the claim directly.",
        provenance=provenance,
    )
    return EvaluationCaseTruth(
        case_id=f"annotation-{split.value}",
        split=split,
        archetype="source-grounded",
        difficulty="hard",
        evidence_condition="direct",
        query=EvaluationQuery(
            query_id="query-1",
            text="What evidence survives?",
            provenance=provenance,
        ),
        qrels=(qrel,),
        claims=(claim,),
        conflict=ConflictExpectation(
            conflict_expected=False,
            rationale="The selected source set contains no conflicting claim.",
        ),
        abstention_expectation=AbstentionExpectation.prohibited,
        provenance=provenance,
    )


def _revision(
    split: EvaluationSplit,
    *,
    revision_id: str = "revision-1",
    parent_revision_sha256: str | None = None,
) -> AnnotationRevision:
    return AnnotationRevision(
        revision_id=revision_id,
        case=_case(split),
        protocol_sha256=_protocol().guidelines_sha256,
        parent_revision_sha256=parent_revision_sha256,
        authored_by="truth-author",
        authored_on=date(2026, 8, 22),
    )


def _review(
    revision: AnnotationRevision,
    number: int,
    *,
    verdict: AnnotationReviewVerdict = AnnotationReviewVerdict.approve,
    conflicts: tuple[AnnotationConflict, ...] = (),
) -> AnnotationReview:
    return AnnotationReview(
        review_id=f"review-{number}",
        revision_sha256=revision.identity_sha256,
        protocol_sha256=_protocol().guidelines_sha256,
        reviewer_id=f"reviewer-{number}",
        reviewed_on=date(2026, 8, 22),
        verdict=verdict,
        rationale="Reviewed from the exact admitted sources without system output.",
        conflicts=conflicts,
    )


def test_development_revision_admission_is_immutable_and_deterministic() -> None:
    protocol = _protocol()
    revision = _revision(EvaluationSplit.development)
    review = _review(revision, 1)
    workflow = IndependentAnnotationWorkflow(protocol)

    first = workflow.admit(revisions=(revision,), reviews=(review,))
    second = workflow.admit(revisions=(revision,), reviews=(review,))

    assert first == second
    assert first.identity_sha256 == second.identity_sha256
    assert first.revision_sha256 == revision.identity_sha256
    assert (
        first.protocol_sha256 == hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest()
    )
    with pytest.raises(ValidationError, match="frozen"):
        revision.authored_by = "changed"  # type: ignore[misc]


def test_heldout_revision_requires_two_distinct_independent_reviewers() -> None:
    revision = _revision(EvaluationSplit.heldout)
    workflow = IndependentAnnotationWorkflow(_protocol())

    with pytest.raises(
        AnnotationWorkflowError,
        match="at least 2 independent reviews",
    ):
        workflow.admit(revisions=(revision,), reviews=(_review(revision, 1),))

    admitted = workflow.admit(
        revisions=(revision,),
        reviews=(_review(revision, 1), _review(revision, 2)),
    )

    assert admitted.split is EvaluationSplit.heldout
    assert admitted.reviewer_ids == ("reviewer-1", "reviewer-2")
    assert admitted.adjudication_id is None


def test_disagreement_retains_conflicts_and_requires_exact_adjudication() -> None:
    revision = _revision(EvaluationSplit.heldout)
    conflict = AnnotationConflict(
        conflict_id="conflict-claim-scope",
        subject_id="claim-1",
        description="Reviewers disagree about whether the claim is sufficiently scoped.",
    )
    reviews = (
        _review(revision, 1),
        _review(
            revision,
            2,
            verdict=AnnotationReviewVerdict.changes_required,
            conflicts=(conflict,),
        ),
    )
    workflow = IndependentAnnotationWorkflow(_protocol())

    with pytest.raises(
        AnnotationWorkflowError,
        match="requires explicit adjudication",
    ):
        workflow.admit(revisions=(revision,), reviews=reviews)

    adjudication = AnnotationAdjudication(
        adjudication_id="adjudication-1",
        revision_sha256=revision.identity_sha256,
        protocol_sha256=_protocol().guidelines_sha256,
        review_ids=tuple(review.review_id for review in reviews),
        adjudicator_id="adjudicator-1",
        adjudicated_on=date(2026, 8, 22),
        verdict=AnnotationAdjudicationVerdict.admit,
        resolved_conflict_ids=(conflict.conflict_id,),
        rationale="The exact source supports the narrower admitted wording.",
    )

    admitted = workflow.admit(
        revisions=(revision,),
        reviews=reviews,
        adjudication=adjudication,
    )

    assert admitted.adjudication_id == adjudication.adjudication_id
    assert admitted.resolved_conflict_ids == (conflict.conflict_id,)


def test_revision_lineage_and_system_output_independence_fail_closed() -> None:
    first = _revision(EvaluationSplit.development)
    broken_successor = _revision(
        EvaluationSplit.development,
        revision_id="revision-2",
        parent_revision_sha256="f" * 64,
    )
    workflow = IndependentAnnotationWorkflow(_protocol())

    with pytest.raises(AnnotationWorkflowError, match="lineage is broken"):
        workflow.admit(
            revisions=(first, broken_successor),
            reviews=(_review(broken_successor, 1),),
        )

    payload = _review(first, 1).model_dump(mode="json")
    payload["system_output_consulted"] = True
    with pytest.raises(ValidationError, match="False"):
        AnnotationReview.model_validate(payload)
