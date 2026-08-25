"""Tests for executable source-first semantic research truth."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bijux_canon_reason.evaluation import (
    AbstentionExpectation,
    ClaimTruthClass,
    EvaluationSplit,
    ResearchQuestionTruthAdapter,
    ResearchTruthAdaptationError,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
RESEARCH_ROOT = REPO_ROOT / "examples/ancient-dna-research"
TRUTH_ROOT = RESEARCH_ROOT / "truth"


def _jsonl(name: str) -> tuple[dict[str, object], ...]:
    return tuple(
        json.loads(line)
        for line in (TRUTH_ROOT / name).read_text(encoding="utf-8").splitlines()
    )


def _source_uris() -> dict[str, str]:
    return {
        path.stem: str(path.relative_to(REPO_ROOT))
        for path in sorted((RESEARCH_ROOT / "corpus/sources").glob("*.xml"))
    }


def test_all_reviewed_development_points_become_executable_truth() -> None:
    cases = ResearchQuestionTruthAdapter().adapt_development(
        cases=_jsonl("evaluation-cases.jsonl"),
        question_claims=_jsonl("question-claim-truth.jsonl"),
        qrels=_jsonl("qrels.jsonl"),
        source_uris=_source_uris(),
    )

    claims = tuple(claim for case in cases for claim in case.claims)
    citations = tuple(label for claim in claims for label in claim.citations)
    assert len(cases) == 12
    assert len(claims) == 31
    assert len(citations) == 48
    assert sum(claim.claim_class is ClaimTruthClass.expected for claim in claims) == 25
    assert sum(claim.claim_class is ClaimTruthClass.forbidden for claim in claims) == 6
    assert {case.split for case in cases} == {EvaluationSplit.development}
    assert (
        sum(
            case.abstention_expectation is AbstentionExpectation.required
            for case in cases
        )
        == 2
    )
    assert all(
        hashlib.sha256((REPO_ROOT / qrel.locator.source_uri).read_bytes()).hexdigest()
        == qrel.locator.source_sha256
        for case in cases
        for qrel in case.qrels
    )


def test_adapter_refuses_system_influenced_or_incomplete_truth() -> None:
    claims = list(_jsonl("question-claim-truth.jsonl"))
    claims[0] = {**claims[0], "system_output_consulted": True}

    with pytest.raises(ResearchTruthAdaptationError, match="independent"):
        ResearchQuestionTruthAdapter().adapt_development(
            cases=_jsonl("evaluation-cases.jsonl"),
            question_claims=tuple(claims),
            qrels=_jsonl("qrels.jsonl"),
            source_uris=_source_uris(),
        )

    with pytest.raises(ResearchTruthAdaptationError, match="development population"):
        ResearchQuestionTruthAdapter().adapt_development(
            cases=_jsonl("evaluation-cases.jsonl"),
            question_claims=_jsonl("question-claim-truth.jsonl")[:-1],
            qrels=_jsonl("qrels.jsonl"),
            source_uris=_source_uris(),
        )
