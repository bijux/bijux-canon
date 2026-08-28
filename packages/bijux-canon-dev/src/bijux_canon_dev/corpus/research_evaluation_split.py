#!/usr/bin/env python3
"""Validate a question-family partition with sealed held-out labels."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping
import json
from pathlib import Path
import sys
from typing import Any

from bijux_canon_dev.corpus.acquisition import canonical, sha256
from bijux_canon_dev.corpus.research_qrels import load_qrels, validate_qrels
from bijux_canon_dev.corpus.research_questions import (
    load_questions,
    validate_questions,
)

SCHEMA_VERSION = "bijux.canon.research_evaluation_split.v2"
CASE_SCHEMA_VERSION = "bijux.canon.research_evaluation_case.v2"
REVIEWER_ID = "bijux-corpus-curation-secondary"
REVIEW_STATUS = "independent_source_review_complete"
REVIEW_METHOD = "independent review of semantic question-family partition"
SPLIT_SEED = "bijux-canon-ancient-dna-question-families-v2"
PARTITIONS = frozenset({"development", "heldout"})
PARTITION_REVIEW_SCHEMA_VERSION = "bijux.canon.research_question_partition_review.v1"


def split_identity(document: Mapping[str, Any]) -> str:
    """Return the canonical identity of a split document."""

    core = {
        key: value for key, value in document.items() if key != "split_identity_sha256"
    }
    return sha256(canonical(core))


def case_identity(record: Mapping[str, Any]) -> str:
    """Return the canonical identity of one partition case."""

    core = {
        key: value for key, value in record.items() if key != "case_identity_sha256"
    }
    return sha256(canonical(core))


def question_label_identity(record: Mapping[str, Any]) -> str:
    """Return the exact identity of one reviewed question and all its labels."""

    return sha256(canonical(record))


def partition_review_identity(record: Mapping[str, Any]) -> str:
    """Return the exact identity of one source-reviewed partition decision."""

    return sha256(canonical(record))


def load_split(path: Path) -> dict[str, Any]:
    """Load a canonical split document from a regular, non-symlink JSON file."""

    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"research evaluation split is not a regular file: {path}")
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict) or canonical(value) + b"\n" != raw:
        raise RuntimeError("research evaluation split is not canonical")
    return value


def load_partition_reviews(path: Path) -> list[dict[str, Any]]:
    """Load canonical source-reviewed family decisions from JSON Lines."""

    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"question partition review is not a regular file: {path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_bytes().splitlines(), 1):
        if not line:
            raise RuntimeError(f"blank question partition review line: {line_number}")
        value = json.loads(line)
        if not isinstance(value, dict) or canonical(value) != line:
            raise RuntimeError(
                f"non-canonical question partition review line: {line_number}"
            )
        records.append(value)
    return records


def _expected_policy() -> dict[str, Any]:
    return {
        "case_construction": "one-case-per-reviewed-semantic-question",
        "development_case_count": 12,
        "heldout_case_count": 6,
        "heldout_labels_available_to_tuning": False,
        "heldout_labels_interface": "release-evaluator-only",
        "split_axis": "evidence-family",
        "split_seed_sha256": sha256(SPLIT_SEED.encode()),
        "system_output_may_define_truth": False,
        "tuning_prohibited_uses": [
            "case-selection",
            "heldout-evidence",
            "heldout-expected-answers",
            "parameters",
            "prompts",
            "reranking",
            "thresholds",
        ],
    }


def _label_set_identity(
    questions: Mapping[str, Mapping[str, Any]], question_ids: list[str]
) -> str:
    return sha256(
        b"".join(
            canonical(questions[question_id]) + b"\n" for question_id in question_ids
        )
    )


def build_split_document(
    reviews: list[dict[str, Any]],
    questions: list[dict[str, Any]],
    *,
    lock_identity_sha256: str,
    qrel_set_sha256: str,
    question_set_sha256: str,
) -> dict[str, Any]:
    """Build the canonical frozen document from independently reviewed decisions."""

    questions_by_id = {str(record["question_id"]): record for record in questions}
    cases: list[dict[str, Any]] = []
    for ordinal, review in enumerate(reviews, 1):
        question = questions_by_id[str(review["question_id"])]
        case: dict[str, Any] = {
            "case_id": f"adna-question-case-{ordinal:03d}",
            "evidence_family": review["evidence_family"],
            "partition_review_sha256": partition_review_identity(review),
            "question_id": review["question_id"],
            "question_label_sha256": question_label_identity(question),
            "schema_version": CASE_SCHEMA_VERSION,
            "split": review["split"],
            "system_output_may_define_truth": False,
        }
        case["case_identity_sha256"] = case_identity(case)
        cases.append(case)
    partition_question_ids = {
        split: [case["question_id"] for case in cases if case["split"] == split]
        for split in ("development", "heldout")
    }
    document: dict[str, Any] = {
        "case_count": len(cases),
        "cases": cases,
        "development_label_set_sha256": _label_set_identity(
            questions_by_id, partition_question_ids["development"]
        ),
        "heldout_label_set_sha256": _label_set_identity(
            questions_by_id, partition_question_ids["heldout"]
        ),
        "lock_identity_sha256": lock_identity_sha256,
        "partition_policy": _expected_policy(),
        "partition_review_set_sha256": sha256(
            b"".join(canonical(record) + b"\n" for record in reviews)
        ),
        "partitions": {
            split: [case["case_id"] for case in cases if case["split"] == split]
            for split in ("development", "heldout")
        },
        "qrel_set_sha256": qrel_set_sha256,
        "question_set_sha256": question_set_sha256,
        "review_method": REVIEW_METHOD,
        "review_status": REVIEW_STATUS,
        "reviewed_on": "2026-08-23",
        "reviewer_id": REVIEWER_ID,
        "schema_version": SCHEMA_VERSION,
    }
    document["case_set_sha256"] = sha256(canonical(cases))
    document["split_identity_sha256"] = split_identity(document)
    return document


def evaluation_case_records(
    document: Mapping[str, Any], questions: tuple[dict[str, Any], ...]
) -> tuple[dict[str, Any], ...]:
    """Project runnable prompts while withholding held-out answer labels."""

    cases = document.get("cases")
    if not isinstance(cases, list):
        raise RuntimeError("research evaluation split cases are not a list")
    questions_by_id = {record["question_id"]: record for record in questions}
    records: list[dict[str, Any]] = []
    for case in cases:
        question = questions_by_id[case["question_id"]]
        record: dict[str, Any] = {
            "case_id": case["case_id"],
            "category": question["category"],
            "evidence_family": case["evidence_family"],
            "label_disposition": (
                "heldout-labels-sealed"
                if case["split"] == "heldout"
                else "development-labels-visible"
            ),
            "question": question["question"],
            "question_id": question["question_id"],
            "schema_version": CASE_SCHEMA_VERSION,
            "split": case["split"],
            "system_output_consulted": False,
            "system_output_may_define_truth": False,
            "truth_sha256": question_label_identity(question),
        }
        if case["split"] == "development":
            record["truth"] = {
                "acceptable_answer_points": question["acceptable_answer_points"],
                "abstention_expected": question["abstention_expected"],
                "answerability": question["answerability"],
                "evidence": question["evidence"],
                "expected_disposition": question["expected_disposition"],
                "rationale": question["rationale"],
                "review_method": question["review_method"],
                "review_status": question["review_status"],
                "reviewed_on": question["reviewed_on"],
                "reviewer_id": question["reviewer_id"],
            }
        record["record_identity_sha256"] = sha256(canonical(record))
        records.append(record)
    return tuple(records)


def write_evaluation_cases(
    document: Mapping[str, Any],
    path: Path,
    *,
    questions: tuple[dict[str, Any], ...],
) -> None:
    """Write canonical runnable cases without exposing held-out labels."""

    records = evaluation_case_records(document, questions)
    path.write_bytes(b"".join(canonical(case) + b"\n" for case in records))


def validate_split(
    document: dict[str, Any],
    *,
    lock_path: Path,
    locator_truth_path: Path,
    partition_review_path: Path,
    qrels_path: Path,
    questions_path: Path,
    research_root: Path,
    split_path: Path,
) -> dict[str, Any]:
    """Validate disjoint families, sealed labels, exact identities, and policy."""

    if split_path.is_symlink() or not split_path.is_file():
        raise RuntimeError("research evaluation split must be a regular file")
    qrels = load_qrels(qrels_path.resolve(strict=True))
    qrel_result = validate_qrels(
        qrels,
        lock_path=lock_path,
        locator_truth_path=locator_truth_path,
        research_root=research_root,
    )
    questions = load_questions(questions_path.resolve(strict=True))
    question_result = validate_questions(questions, qrels_path=qrels_path)
    reviews = load_partition_reviews(partition_review_path.resolve(strict=True))
    review_by_question: dict[str, dict[str, Any]] = {}
    family_partition_from_review: dict[str, str] = {}
    for review in reviews:
        question_id = review.get("question_id")
        family = review.get("evidence_family")
        split = review.get("split")
        expected_review = {
            "review_method": REVIEW_METHOD,
            "review_status": REVIEW_STATUS,
            "reviewed_on": "2026-08-23",
            "reviewer_id": REVIEWER_ID,
            "schema_version": PARTITION_REVIEW_SCHEMA_VERSION,
            "system_output_consulted": False,
            "system_output_may_define_truth": False,
        }
        drift = [
            key for key, value in expected_review.items() if review.get(key) != value
        ]
        if (
            drift
            or not isinstance(question_id, str)
            or question_id in review_by_question
            or question_id not in {str(item["question_id"]) for item in questions}
            or not isinstance(family, str)
            or not family.startswith("adna-evidence-")
            or split not in PARTITIONS
            or not isinstance(review.get("rationale"), str)
            or len(review["rationale"]) < 60
        ):
            raise RuntimeError(f"invalid question partition review: {question_id}")
        previous_partition = family_partition_from_review.setdefault(family, str(split))
        if previous_partition != split:
            raise RuntimeError(f"reviewed evidence family crosses partitions: {family}")
        review_by_question[question_id] = review
    if set(review_by_question) != {str(item["question_id"]) for item in questions}:
        raise RuntimeError("question partition review coverage mismatch")
    required = {
        "case_count": 18,
        "lock_identity_sha256": qrels[0]["lock_identity_sha256"],
        "partition_policy": _expected_policy(),
        "partition_review_set_sha256": sha256(
            b"".join(canonical(record) + b"\n" for record in reviews)
        ),
        "qrel_set_sha256": qrel_result["qrel_set_sha256"],
        "question_set_sha256": question_result["question_set_sha256"],
        "review_method": REVIEW_METHOD,
        "review_status": REVIEW_STATUS,
        "reviewed_on": "2026-08-23",
        "reviewer_id": REVIEWER_ID,
        "schema_version": SCHEMA_VERSION,
    }
    drift = [key for key, value in required.items() if document.get(key) != value]
    if drift:
        raise RuntimeError(f"research evaluation split metadata drift: {drift}")

    cases = document.get("cases")
    if not isinstance(cases, list) or len(cases) != len(questions):
        raise RuntimeError("research evaluation split question coverage mismatch")
    questions_by_id = {str(record["question_id"]): record for record in questions}
    question_ids: set[str] = set()
    case_ids: set[str] = set()
    split_counts: Counter[str] = Counter()
    family_partition: dict[str, str] = {}
    partition_question_ids: dict[str, list[str]] = {
        "development": [],
        "heldout": [],
    }
    partition_category_counts: dict[str, Counter[str]] = {
        "development": Counter(),
        "heldout": Counter(),
    }
    for ordinal, case in enumerate(cases, 1):
        if not isinstance(case, dict):
            raise RuntimeError("research evaluation split case is not an object")
        case_id = case.get("case_id")
        question_id = case.get("question_id")
        family = case.get("evidence_family")
        split = case.get("split")
        question = questions_by_id.get(str(question_id))
        if (
            case_id != f"adna-question-case-{ordinal:03d}"
            or case_id in case_ids
            or question is None
            or question_id in question_ids
            or not isinstance(family, str)
            or not family.startswith("adna-evidence-")
            or split not in PARTITIONS
        ):
            raise RuntimeError(f"invalid question partition binding: {case_id}")
        expected_case = {
            "evidence_family": review_by_question[str(question_id)]["evidence_family"],
            "partition_review_sha256": partition_review_identity(
                review_by_question[str(question_id)]
            ),
            "question_label_sha256": question_label_identity(question),
            "schema_version": CASE_SCHEMA_VERSION,
            "split": review_by_question[str(question_id)]["split"],
            "system_output_may_define_truth": False,
        }
        case_drift = [
            key for key, value in expected_case.items() if case.get(key) != value
        ]
        if case_drift:
            raise RuntimeError(
                f"question partition case drift: {case_id}: {case_drift}"
            )
        previous_partition = family_partition.setdefault(family, str(split))
        if previous_partition != split:
            raise RuntimeError(f"evidence family crosses partitions: {family}")
        if case.get("case_identity_sha256") != case_identity(case):
            raise RuntimeError(f"question partition case identity mismatch: {case_id}")
        case_ids.add(str(case_id))
        question_ids.add(str(question_id))
        split_counts[str(split)] += 1
        partition_question_ids[str(split)].append(str(question_id))
        partition_category_counts[str(split)][str(question["category"])] += 1
    if question_ids != set(questions_by_id):
        raise RuntimeError("research evaluation split question coverage mismatch")
    if split_counts != Counter({"development": 12, "heldout": 6}):
        raise RuntimeError("research evaluation partition count mismatch")
    if set(family_partition.values()) != PARTITIONS:
        raise RuntimeError("research evaluation family partition coverage mismatch")
    if len(partition_category_counts["heldout"]) < 6:
        raise RuntimeError("held-out semantic category diversity mismatch")
    expected_partitions = {
        split: [case["case_id"] for case in cases if case["split"] == split]
        for split in ("development", "heldout")
    }
    if document.get("partitions") != expected_partitions:
        raise RuntimeError("research evaluation partition index mismatch")
    expected_label_sets = {
        f"{split}_label_set_sha256": _label_set_identity(
            questions_by_id, partition_question_ids[split]
        )
        for split in ("development", "heldout")
    }
    label_drift = [
        key for key, value in expected_label_sets.items() if document.get(key) != value
    ]
    if label_drift:
        raise RuntimeError(f"research evaluation label-set drift: {label_drift}")
    case_set_sha256 = sha256(canonical(cases))
    if document.get("case_set_sha256") != case_set_sha256:
        raise RuntimeError("research evaluation case-set identity mismatch")
    if document.get("split_identity_sha256") != split_identity(document):
        raise RuntimeError("research evaluation split identity mismatch")
    return {
        "case_count": len(cases),
        "case_set_sha256": case_set_sha256,
        "development_case_count": split_counts["development"],
        "development_category_count": len(partition_category_counts["development"]),
        "development_family_count": sum(
            split == "development" for split in family_partition.values()
        ),
        "development_label_set_sha256": expected_label_sets[
            "development_label_set_sha256"
        ],
        "family_overlap_count": 0,
        "heldout_case_count": split_counts["heldout"],
        "heldout_category_count": len(partition_category_counts["heldout"]),
        "heldout_family_count": sum(
            split == "heldout" for split in family_partition.values()
        ),
        "heldout_label_set_sha256": expected_label_sets["heldout_label_set_sha256"],
        "heldout_labels_available_to_tuning": False,
        "leakage_free": True,
        "question_count": len(question_ids),
        "question_overlap_count": 0,
        "split_identity_sha256": document["split_identity_sha256"],
    }


def main() -> None:
    """Validate the durable question-family partition."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--locator-truth", type=Path, required=True)
    parser.add_argument("--partition-review", type=Path, required=True)
    parser.add_argument("--qrels", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--cases-output", type=Path)
    args = parser.parse_args()
    document = load_split(args.split)
    result = validate_split(
        document,
        lock_path=args.lock,
        locator_truth_path=args.locator_truth,
        partition_review_path=args.partition_review,
        qrels_path=args.qrels,
        questions_path=args.questions,
        research_root=args.research_root,
        split_path=args.split,
    )
    if args.cases_output is not None:
        write_evaluation_cases(
            document,
            args.cases_output,
            questions=tuple(load_questions(args.questions)),
        )
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
