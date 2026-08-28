#!/usr/bin/env python3
"""Score held-out retrieval through an aggregate-only release boundary."""

from __future__ import annotations

import argparse
import json
from math import log2
import os
from pathlib import Path
import sys
from typing import Any

from bijux_canon_dev.corpus.acquisition import canonical
from bijux_canon_dev.corpus.research_evaluation_split import (
    load_split,
    validate_split,
)
from bijux_canon_dev.corpus.research_questions import load_questions

SCHEMA_VERSION = "bijux.canon.release_retrieval_evaluation.v1"
AUTHORIZATION_ENV = "BIJUX_CANON_RELEASE_EVALUATION"


def load_submissions(path: Path) -> list[dict[str, Any]]:
    """Load canonical submitted rankings without silently skipping rows."""

    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"release submission is not a regular file: {path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_bytes().splitlines(), 1):
        if not line:
            raise RuntimeError(f"blank release submission line: {line_number}")
        value = json.loads(line)
        if not isinstance(value, dict) or canonical(value) != line:
            raise RuntimeError(f"non-canonical release submission line: {line_number}")
        records.append(value)
    return records


def _reciprocal_rank(ranking: list[str], relevant: set[str], *, limit: int) -> float:
    for rank, qrel_id in enumerate(ranking[:limit], 1):
        if qrel_id in relevant:
            return 1.0 / rank
    return 0.0


def _ndcg(ranking: list[str], grades: dict[str, int], *, limit: int) -> float:
    observed = sum(
        (2 ** grades.get(qrel_id, 0) - 1) / log2(rank + 1)
        for rank, qrel_id in enumerate(ranking[:limit], 1)
    )
    ideal = sum(
        (2**grade - 1) / log2(rank + 1)
        for rank, grade in enumerate(sorted(grades.values(), reverse=True)[:limit], 1)
    )
    return observed / ideal if ideal else 0.0


def evaluate_heldout_retrieval(
    submissions: list[dict[str, Any]],
    *,
    authorization: str | None,
    document: dict[str, Any],
    questions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return aggregate held-out metrics without returning answer or evidence labels."""

    split_identity = str(document["split_identity_sha256"])
    if authorization != split_identity:
        raise RuntimeError(
            f"release evaluation requires {AUTHORIZATION_ENV}=<split identity>"
        )
    cases = document.get("cases")
    if not isinstance(cases, list):
        raise RuntimeError("release evaluation split cases are invalid")
    heldout_cases = [case for case in cases if case.get("split") == "heldout"]
    heldout_ids = {str(case["question_id"]) for case in heldout_cases}
    submitted: dict[str, list[str]] = {}
    for record in submissions:
        question_id = record.get("question_id")
        ranking = record.get("retrieved_qrel_ids")
        if (
            not isinstance(question_id, str)
            or question_id not in heldout_ids
            or question_id in submitted
            or not isinstance(ranking, list)
            or len(ranking) > 100
            or any(not isinstance(qrel_id, str) for qrel_id in ranking)
            or len(ranking) != len(set(ranking))
        ):
            raise RuntimeError(f"invalid held-out retrieval submission: {question_id}")
        submitted[question_id] = ranking
    if set(submitted) != heldout_ids:
        raise RuntimeError("held-out retrieval submission population mismatch")

    questions_by_id = {str(record["question_id"]): record for record in questions}
    recall_at_5: list[float] = []
    reciprocal_rank_at_10: list[float] = []
    ndcg_at_10: list[float] = []
    for question_id in sorted(heldout_ids):
        evidence = questions_by_id[question_id]["evidence"]
        grades = {
            str(item["qrel_id"]): int(item["relevance_grade"]) for item in evidence
        }
        relevant = set(grades)
        ranking = submitted[question_id]
        recall_at_5.append(len(set(ranking[:5]) & relevant) / len(relevant))
        reciprocal_rank_at_10.append(_reciprocal_rank(ranking, relevant, limit=10))
        ndcg_at_10.append(_ndcg(ranking, grades, limit=10))
    count = len(heldout_ids)
    return {
        "heldout_label_set_sha256": document["heldout_label_set_sha256"],
        "macro_mrr_at_10": sum(reciprocal_rank_at_10) / count,
        "macro_ndcg_at_10": sum(ndcg_at_10) / count,
        "macro_recall_at_5": sum(recall_at_5) / count,
        "minimum_recall_at_5": min(recall_at_5),
        "question_count": count,
        "schema_version": SCHEMA_VERSION,
        "split_identity_sha256": split_identity,
    }


def main() -> None:
    """Validate the sealed split and score one complete held-out submission."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--locator-truth", type=Path, required=True)
    parser.add_argument("--partition-review", type=Path, required=True)
    parser.add_argument("--qrels", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--submission", type=Path, required=True)
    args = parser.parse_args()
    document = load_split(args.split)
    validate_split(
        document,
        lock_path=args.lock,
        locator_truth_path=args.locator_truth,
        partition_review_path=args.partition_review,
        qrels_path=args.qrels,
        questions_path=args.questions,
        research_root=args.research_root,
        split_path=args.split,
    )
    result = evaluate_heldout_retrieval(
        load_submissions(args.submission),
        authorization=os.environ.get(AUTHORIZATION_ENV),
        document=document,
        questions=load_questions(args.questions),
    )
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
