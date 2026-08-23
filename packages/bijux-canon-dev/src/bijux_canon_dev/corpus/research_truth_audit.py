#!/usr/bin/env python3
"""Audit semantic populations, review lineage, and question-family leakage."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
import json
from pathlib import Path
import sys
from typing import Any

from bijux_canon_dev.corpus.acquisition import canonical, sha256
from bijux_canon_dev.corpus.research_claim_truth import load_claim_truth
from bijux_canon_dev.corpus.research_evaluation_split import (
    load_split,
    question_label_identity,
)
from bijux_canon_dev.corpus.research_qrels import load_qrels
from bijux_canon_dev.corpus.research_questions import (
    load_questions,
    validate_questions,
)

SCHEMA_VERSION = "bijux.canon.research_truth_audit.v3"


def _load_jsonl(path: Path) -> tuple[dict[str, Any], ...]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"research truth is not a regular file: {path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_bytes().splitlines(), 1):
        if not line:
            raise RuntimeError(f"blank research truth row {line_number}: {path}")
        value = json.loads(line)
        if not isinstance(value, dict) or canonical(value) != line:
            raise RuntimeError(
                f"non-canonical research truth row {line_number}: {path}"
            )
        records.append(value)
    return tuple(records)


def _duplicates(values: Iterable[str]) -> list[str]:
    return sorted(value for value, count in Counter(values).items() if count > 1)


def _string_set(records: Iterable[Mapping[str, Any]], key: str) -> set[str]:
    return {str(record[key]) for record in records}


def _provenance(
    records: Iterable[Mapping[str, Any]],
    *,
    reviewer_key: str,
    method_key: str,
    output_consulted_key: str | None = None,
) -> dict[str, Any]:
    rows = tuple(records)
    consulted = (
        sorted({bool(record[output_consulted_key]) for record in rows})
        if output_consulted_key is not None
        and all(output_consulted_key in record for record in rows)
        else []
    )
    return {
        "reviewer_ids": sorted(_string_set(rows, reviewer_key)),
        "reviewed_on": sorted(_string_set(rows, "reviewed_on")),
        "review_methods": sorted(_string_set(rows, method_key)),
        "system_output_consulted": consulted,
        "system_output_consulted_declared": bool(consulted),
    }


def _field_conflicts(
    records: Iterable[Mapping[str, Any]],
    *,
    identity_key: str,
    value_keys: tuple[str, ...],
) -> list[str]:
    observed: dict[str, set[tuple[str, ...]]] = defaultdict(set)
    for record in records:
        observed[str(record[identity_key])].add(
            tuple(str(record[key]) for key in value_keys)
        )
    return sorted(identity for identity, values in observed.items() if len(values) > 1)


def _partition_report(cases: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    populations: dict[str, dict[str, set[str]]] = {
        split: {"case": set(), "family": set(), "question": set()}
        for split in ("development", "heldout")
    }
    for case in cases:
        split = str(case["split"])
        if split not in populations:
            continue
        populations[split]["case"].add(str(case["case_id"]))
        populations[split]["family"].add(str(case["evidence_family"]))
        populations[split]["question"].add(str(case["question_id"]))
    overlaps = {
        name: sorted(populations["development"][name] & populations["heldout"][name])
        for name in ("case", "family", "question")
    }
    return {
        "development": {
            f"{name}_count": len(values)
            for name, values in populations["development"].items()
        },
        "heldout": {
            f"{name}_count": len(values)
            for name, values in populations["heldout"].items()
        },
        "overlap": {f"{name}_count": len(values) for name, values in overlaps.items()},
        "overlap_ids": overlaps,
        "leakage_free": not any(overlaps.values()),
    }


def audit_research_truth(
    *,
    cases_path: Path,
    claim_truth_path: Path,
    qrels_path: Path,
    questions_path: Path,
    split_path: Path,
) -> dict[str, Any]:
    """Return a canonical audit whose denominator is semantic questions."""

    qrels = tuple(load_qrels(qrels_path))
    questions = tuple(load_questions(questions_path))
    validate_questions(list(questions), qrels_path=qrels_path)
    claims = tuple(load_claim_truth(claim_truth_path))
    cases = _load_jsonl(cases_path)
    split = load_split(split_path)

    legacy_query_ids = _string_set(qrels, "query_id")
    legacy_query_texts = _string_set(qrels, "query")
    question_ids = _string_set(questions, "question_id")
    question_texts = _string_set(questions, "question")
    qrel_ids = _string_set(qrels, "qrel_id")
    claim_ids = _string_set(claims, "truth_id")
    claim_identities = _string_set(claims, "claim_identity_sha256")
    case_ids = _string_set(cases, "case_id")
    source_ids = _string_set(qrels, "source_id") | _string_set(claims, "source_id")

    legacy_query_inventory: dict[str, dict[str, Any]] = {}
    for query_id in sorted(legacy_query_ids):
        matching = [record for record in qrels if record["query_id"] == query_id]
        legacy_query_inventory[query_id] = {
            "question": sorted({str(record["query"]) for record in matching}),
            "qrel_ids": sorted(str(record["qrel_id"]) for record in matching),
            "qrel_row_count": len(matching),
            "source_ids": sorted(str(record["source_id"]) for record in matching),
        }
    qrel_inventory = {
        str(record["qrel_id"]): {
            "adjudication_status": str(record["adjudication_status"]),
            "legacy_query_id": str(record["query_id"]),
            "legacy_relevance_grade": int(record["relevance_grade"]),
            "source_id": str(record["source_id"]),
        }
        for record in sorted(qrels, key=lambda item: str(item["qrel_id"]))
    }
    claim_inventory = {
        str(record["truth_id"]): {
            "abstention_expected": bool(record["abstention_expected"]),
            "claim_class": str(record["claim_class"]),
            "claim_identity_sha256": str(record["claim_identity_sha256"]),
            "evidence_relation": str(record["evidence_relation"]),
            "source_id": str(record["source_id"]),
            "statement": str(record["claim"]),
            "verdict": str(record["verdict"]),
        }
        for record in sorted(claims, key=lambda item: str(item["truth_id"]))
    }
    question_inventory = {
        str(record["question_id"]): {
            "abstention_expected": bool(record["abstention_expected"]),
            "answerability": str(record["answerability"]),
            "category": str(record["category"]),
            "evidence": [
                {
                    "qrel_id": str(item["qrel_id"]),
                    "relation": str(item["relation"]),
                    "relevance_grade": int(item["relevance_grade"]),
                }
                for item in record["evidence"]
            ],
            "question": str(record["question"]),
        }
        for record in sorted(questions, key=lambda item: str(item["question_id"]))
    }

    questions_by_id = {str(record["question_id"]): record for record in questions}
    split_cases_value = split.get("cases")
    split_cases = (
        tuple(item for item in split_cases_value if isinstance(item, dict))
        if isinstance(split_cases_value, list)
        else ()
    )
    consistency = {
        "development_cases_expose_reviewed_truth": all(
            case.get("split") != "development" or isinstance(case.get("truth"), dict)
            for case in cases
        ),
        "heldout_cases_seal_reviewed_truth": all(
            case.get("split") != "heldout"
            or (
                "truth" not in case
                and case.get("label_disposition") == "heldout-labels-sealed"
            )
            for case in cases
        ),
        "case_question_bindings_match_truth": all(
            str(case["question_id"]) in questions_by_id
            and str(case["question"])
            == str(questions_by_id[str(case["question_id"])]["question"])
            and str(case["truth_sha256"])
            == question_label_identity(questions_by_id[str(case["question_id"])])
            for case in cases
        ),
        "split_case_ids_match_execution_rows": _string_set(split_cases, "case_id")
        == case_ids,
        "split_question_ids_match_execution_rows": _string_set(
            split_cases, "question_id"
        )
        == _string_set(cases, "question_id"),
    }

    duplicates = {
        "case_ids": _duplicates(str(record["case_id"]) for record in cases),
        "claim_identities": _duplicates(
            str(record["claim_identity_sha256"]) for record in claims
        ),
        "claim_truth_ids": _duplicates(str(record["truth_id"]) for record in claims),
        "qrel_ids": _duplicates(str(record["qrel_id"]) for record in qrels),
        "question_ids": _duplicates(str(record["question_id"]) for record in questions),
        "question_texts": _duplicates(str(record["question"]) for record in questions),
    }
    contradictions = {
        "claim_identity_values": _field_conflicts(
            claims,
            identity_key="claim_identity_sha256",
            value_keys=("claim", "claim_class", "verdict", "evidence_relation"),
        ),
        "claim_truth_values": _field_conflicts(
            claims,
            identity_key="truth_id",
            value_keys=("claim", "claim_class", "verdict", "evidence_relation"),
        ),
        "legacy_query_texts": _field_conflicts(
            qrels,
            identity_key="query_id",
            value_keys=("query",),
        ),
        "question_values": _field_conflicts(
            questions,
            identity_key="question_id",
            value_keys=("question", "category", "answerability"),
        ),
    }

    qrel_provenance = _provenance(
        qrels,
        reviewer_key="adjudicator_id",
        method_key="review_method",
        output_consulted_key="system_ranking_consulted",
    )
    claim_provenance = _provenance(
        claims,
        reviewer_key="reviewer_id",
        method_key="review_method",
    )
    question_provenance = _provenance(
        questions,
        reviewer_key="reviewer_id",
        method_key="review_method",
        output_consulted_key="system_output_consulted",
    )
    independent_review_complete = (
        len(qrel_provenance["reviewer_ids"]) > 1
        and len(claim_provenance["reviewer_ids"]) > 1
    )
    partition = _partition_report(cases)
    review_queue = []
    if not independent_review_complete:
        review_queue.append(
            {
                "affected_population": "legacy-qrels-and-atomic-claims",
                "issue_id": "independent-review-required",
                "reason": "legacy qrels and claim truth each have only one primary reviewer",
                "status": "review-required",
            }
        )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "inventory": {
            "case_row_count": len(cases),
            "legacy_qrel_query_count": len(legacy_query_ids),
            "legacy_qrel_query_text_count": len(legacy_query_texts),
            "reviewed_semantic_question_count": len(question_ids),
            "reviewed_semantic_question_text_count": len(question_texts),
            "source_count": len(source_ids),
            "unique_case_count": len(case_ids),
            "unique_claim_count": len(claim_ids),
            "unique_claim_identity_count": len(claim_identities),
            "unique_qrel_count": len(qrel_ids),
        },
        "case_label_disposition_counts": dict(
            sorted(
                Counter(str(record["label_disposition"]) for record in cases).items()
            )
        ),
        "claim_class_counts": dict(
            sorted(Counter(str(record["claim_class"]) for record in claims).items())
        ),
        "claim_inventory": claim_inventory,
        "claim_verdict_counts": dict(
            sorted(Counter(str(record["verdict"]) for record in claims).items())
        ),
        "contradictions": contradictions,
        "dataset_consistency": consistency,
        "duplicates": duplicates,
        "legacy_query_inventory": legacy_query_inventory,
        "partition": partition,
        "qrel_inventory": qrel_inventory,
        "question_answerability_counts": dict(
            sorted(
                Counter(str(record["answerability"]) for record in questions).items()
            )
        ),
        "question_category_counts": dict(
            sorted(Counter(str(record["category"]) for record in questions).items())
        ),
        "question_inventory": question_inventory,
        "release_eligible": False,
        "review_provenance": {
            "claims": claim_provenance,
            "independent_legacy_truth_review_complete": independent_review_complete,
            "label_status": "semantic-questions-independent-legacy-truth-review-required",
            "qrels": qrel_provenance,
            "questions": question_provenance,
            "split": {
                "review_methods": [str(split["review_method"])],
                "reviewed_on": [str(split["reviewed_on"])],
                "reviewer_ids": [str(split["reviewer_id"])],
                "system_output_may_define_truth": bool(
                    split["partition_policy"]["system_output_may_define_truth"]
                ),
            },
        },
        "review_queue": review_queue,
    }
    report["release_eligible"] = not (
        any(duplicates.values())
        or any(contradictions.values())
        or not all(consistency.values())
        or review_queue
        or not partition["leakage_free"]
    )
    report["audit_identity_sha256"] = sha256(canonical(report))
    return report


def main() -> None:
    """Print the stable semantic-population audit."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--claim-truth", type=Path, required=True)
    parser.add_argument("--qrels", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    args = parser.parse_args()
    json.dump(
        audit_research_truth(
            cases_path=args.cases,
            claim_truth_path=args.claim_truth,
            qrels_path=args.qrels,
            questions_path=args.questions,
            split_path=args.split,
        ),
        sys.stdout,
        indent=2,
        sort_keys=True,
    )
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
