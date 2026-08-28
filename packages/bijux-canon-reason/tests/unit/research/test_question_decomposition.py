# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Bounded research-question decomposition tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from pydantic import ValidationError
import pytest

from bijux_canon_reason.research import (
    QuestionDecomposer,
    QuestionDecompositionError,
    QuestionDecompositionErrorCode,
    QuestionDecompositionPolicy,
    ResearchQuestion,
    SubquestionCandidate,
    SubquestionDisposition,
    create_subquestion_candidate,
)

_REPO = Path(__file__).resolve().parents[5]
_API_ROOT = _REPO / "apis/bijux-canon-reason/v2"


def _real_question() -> ResearchQuestion:
    records = json.loads(
        (_API_ROOT / "examples/evaluation-claim-records.json").read_text()
    )["records"]
    record = next(
        item
        for item in records
        if item["artifact_type"] == "bijux.canon.reason.question"
    )
    return ResearchQuestion.model_validate(record)


def _candidate(
    text: str,
    priority: int,
    *,
    rationale: str = "This evidence need resolves part of the root question.",
    scope_artifact_id: str | None = None,
) -> SubquestionCandidate:
    question = _real_question()
    return create_subquestion_candidate(
        text=text,
        scope_artifact_id=scope_artifact_id or question.scope_artifact_id,
        rationale=rationale,
        evidence_needs=("exact source span", "relation classification"),
        priority=priority,
    )


def test_real_question_decomposes_with_duplicate_overlap_and_budget_decisions() -> None:
    question = _real_question()
    candidates = (
        _candidate("Which admitted source text directly defines FASTQ?", 100),
        _candidate(
            "What admitted source text directly defines FASTQ?",
            95,
            rationale="A differently phrased duplicate must remain auditable.",
        ),
        _candidate("Which admitted source text directly describes FASTQ?", 90),
        _candidate(
            "What quality encoding details does the admitted FASTQ source report?",
            80,
        ),
        _candidate("How is the FASTQ record structure organized into lines?", 70),
    )
    result = QuestionDecomposer(
        QuestionDecompositionPolicy(max_candidates=5, max_subquestions=2)
    ).decompose(question, candidates)

    assert tuple(item.text for item in result.subquestions) == (
        "Which admitted source text directly defines FASTQ?",
        "What quality encoding details does the admitted FASTQ source report?",
    )
    assert tuple(decision.disposition for decision in result.decisions) == (
        SubquestionDisposition.selected,
        SubquestionDisposition.duplicate,
        SubquestionDisposition.overlap,
        SubquestionDisposition.selected,
        SubquestionDisposition.subquestion_budget,
    )
    assert result.decisions[1].lexical_overlap == 1.0
    assert result.decisions[2].lexical_overlap >= 0.8
    assert all(
        item.parent_question_artifact_id == question.artifact_id
        and item.scope_artifact_id == question.scope_artifact_id
        and item.evidence_needs
        for item in result.subquestions
    )


def test_candidate_order_does_not_change_decomposition_identity() -> None:
    question = _real_question()
    candidates = (
        _candidate("Which exact source text defines FASTQ?", 90),
        _candidate("What quality encoding does the FASTQ source report?", 80),
        _candidate("How many lines form each FASTQ record?", 70),
    )
    decomposer = QuestionDecomposer()

    forward = decomposer.decompose(question, candidates)
    reverse = decomposer.decompose(question, tuple(reversed(candidates)))

    assert forward == reverse
    assert forward.artifact_id == reverse.artifact_id


def test_same_text_in_distinct_scopes_is_not_collapsed() -> None:
    question = _real_question()
    first_scope = "sha256:" + "1" * 64
    second_scope = "sha256:" + "2" * 64
    candidates = (
        _candidate(
            "Which source reports the quality encoding?",
            90,
            scope_artifact_id=first_scope,
        ),
        _candidate(
            "Which source reports the quality encoding?",
            80,
            scope_artifact_id=second_scope,
        ),
    )

    result = QuestionDecomposer().decompose(question, candidates)

    assert len(result.subquestions) == 2
    assert all(
        decision.disposition is SubquestionDisposition.selected
        for decision in result.decisions
    )


def test_unanswerable_candidate_is_rejected_without_consuming_budget() -> None:
    result = QuestionDecomposer(
        QuestionDecompositionPolicy(max_candidates=2, max_subquestions=1)
    ).decompose(
        _real_question(),
        (
            _candidate("FASTQ format?", 100),
            _candidate("Which exact source sentence defines FASTQ?", 90),
        ),
    )

    assert len(result.subquestions) == 1
    assert tuple(decision.disposition for decision in result.decisions) == (
        SubquestionDisposition.unanswerable,
        SubquestionDisposition.selected,
    )


def test_subquestions_validate_against_the_public_v2_schema() -> None:
    result = QuestionDecomposer().decompose(
        _real_question(),
        (_candidate("Which exact source sentence defines FASTQ?", 90),),
    )
    schema = json.loads((_API_ROOT / "reasoning-artifacts.schema.json").read_text())
    validator = Draft202012Validator(schema)

    validator.validate(result.subquestions[0].model_dump(mode="json"))


def test_hard_input_budgets_fail_with_stable_codes() -> None:
    question = _real_question()
    candidate = _candidate("Which exact source sentence defines FASTQ?", 90)

    with pytest.raises(QuestionDecompositionError) as candidate_error:
        QuestionDecomposer(
            QuestionDecompositionPolicy(max_candidates=1, max_subquestions=1)
        ).decompose(question, (candidate, _candidate("How is FASTQ structured?", 80)))
    assert (
        candidate_error.value.code
        is QuestionDecompositionErrorCode.candidate_budget_exceeded
    )

    with pytest.raises(QuestionDecompositionError) as identity_error:
        QuestionDecomposer().decompose(question, (candidate, candidate))
    assert (
        identity_error.value.code
        is QuestionDecompositionErrorCode.duplicate_candidate_identity
    )


def test_tampered_root_identity_fails_closed() -> None:
    record = _real_question().model_dump(mode="json")
    tampered = copy.deepcopy(record)
    tampered["text"] = "What was silently changed?"

    with pytest.raises(ValidationError, match="hash|identity"):
        ResearchQuestion.model_validate(tampered)
