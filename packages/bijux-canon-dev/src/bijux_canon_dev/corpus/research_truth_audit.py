#!/usr/bin/env python3
"""Audit semantic populations, review lineage, and leakage in research truth."""

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
from bijux_canon_dev.corpus.research_evaluation_split import load_split
from bijux_canon_dev.corpus.research_qrels import load_qrels

SCHEMA_VERSION = "bijux.canon.research_truth_audit.v1"


def _load_jsonl(path: Path) -> tuple[dict[str, Any], ...]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"research truth is not a regular file: {path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise RuntimeError(
                f"research truth row {line_number} is not an object: {path}"
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
        split: {"case": set(), "query": set(), "qrel": set(), "claim": set()}
        for split in ("development", "heldout")
    }
    for case in cases:
        split = str(case["split"])
        if split not in populations:
            continue
        populations[split]["case"].add(str(case["case_id"]))
        populations[split]["query"].add(str(case["query_id"]))
        populations[split]["qrel"].add(str(case["qrel_id"]))
        populations[split]["claim"].add(str(case["claim_truth_id"]))
    overlaps = {
        name: sorted(populations["development"][name] & populations["heldout"][name])
        for name in ("case", "query", "qrel", "claim")
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
    split_path: Path,
) -> dict[str, Any]:
    """Return a canonical audit without treating execution rows as questions."""

    qrels = tuple(load_qrels(qrels_path))
    claims = tuple(load_claim_truth(claim_truth_path))
    cases = _load_jsonl(cases_path)
    split = load_split(split_path)

    query_ids = _string_set(qrels, "query_id")
    query_texts = _string_set(qrels, "query")
    qrel_ids = _string_set(qrels, "qrel_id")
    claim_ids = _string_set(claims, "truth_id")
    claim_identities = _string_set(claims, "claim_identity_sha256")
    case_ids = _string_set(cases, "case_id")
    pairs = {(str(case["qrel_id"]), str(case["claim_truth_id"])) for case in cases}
    source_ids = _string_set(qrels, "source_id") | _string_set(claims, "source_id")

    query_rows: dict[str, dict[str, Any]] = {}
    for query_id in sorted(query_ids):
        matching = [record for record in qrels if record["query_id"] == query_id]
        query_rows[query_id] = {
            "question": sorted({str(record["query"]) for record in matching}),
            "qrel_row_count": len(matching),
            "qrel_ids": sorted(str(record["qrel_id"]) for record in matching),
            "source_ids": sorted(str(record["source_id"]) for record in matching),
        }
    qrel_inventory = {
        str(record["qrel_id"]): {
            "query_id": str(record["query_id"]),
            "source_id": str(record["source_id"]),
            "relevance_grade": int(record["relevance_grade"]),
            "adjudication_status": str(record["adjudication_status"]),
        }
        for record in sorted(qrels, key=lambda item: str(item["qrel_id"]))
    }
    claim_inventory = {
        str(record["truth_id"]): {
            "claim_identity_sha256": str(record["claim_identity_sha256"]),
            "source_id": str(record["source_id"]),
            "statement": str(record["claim"]),
            "claim_class": str(record["claim_class"]),
            "verdict": str(record["verdict"]),
            "evidence_relation": str(record["evidence_relation"]),
            "abstention_expected": bool(record["abstention_expected"]),
        }
        for record in sorted(claims, key=lambda item: str(item["truth_id"]))
    }

    source_cross_products = []
    for source_id in sorted(source_ids):
        source_qrels = [record for record in qrels if record["source_id"] == source_id]
        source_claims = [
            record for record in claims if record["source_id"] == source_id
        ]
        source_cases = [record for record in cases if record["source_id"] == source_id]
        source_cross_products.append(
            {
                "source_id": source_id,
                "query_count": len(_string_set(source_qrels, "query_id")),
                "qrel_count": len(source_qrels),
                "claim_count": len(source_claims),
                "case_row_count": len(source_cases),
                "expected_cross_product_count": len(source_qrels) * len(source_claims),
            }
        )
    split_cases_value = split.get("cases")
    split_cases = (
        tuple(item for item in split_cases_value if isinstance(item, dict))
        if isinstance(split_cases_value, list)
        else ()
    )
    qrels_by_id = {str(record["qrel_id"]): record for record in qrels}
    claims_by_id = {str(record["truth_id"]): record for record in claims}
    consistency = {
        "case_query_bindings_match_qrels": all(
            str(case["qrel_id"]) in qrels_by_id
            and str(case["query_id"])
            == str(qrels_by_id[str(case["qrel_id"])]["query_id"])
            for case in cases
        ),
        "case_claim_bindings_match_truth": all(
            str(case["claim_truth_id"]) in claims_by_id
            and str(case["source_id"])
            == str(claims_by_id[str(case["claim_truth_id"])]["source_id"])
            for case in cases
        ),
        "source_cross_products_complete": all(
            item["case_row_count"] == item["expected_cross_product_count"]
            for item in source_cross_products
        ),
        "split_case_ids_match_execution_rows": _string_set(split_cases, "case_id")
        == case_ids,
        "split_truth_pairs_match_execution_rows": {
            (str(case["qrel_id"]), str(case["claim_truth_id"])) for case in split_cases
        }
        == pairs,
    }

    duplicates = {
        "case_ids": _duplicates(str(record["case_id"]) for record in cases),
        "claim_identities": _duplicates(
            str(record["claim_identity_sha256"]) for record in claims
        ),
        "claim_truth_ids": _duplicates(str(record["truth_id"]) for record in claims),
        "qrel_claim_pairs": _duplicates(
            f"{record['qrel_id']}::{record['claim_truth_id']}" for record in cases
        ),
        "qrel_ids": _duplicates(str(record["qrel_id"]) for record in qrels),
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
        "query_texts": _field_conflicts(
            qrels,
            identity_key="query_id",
            value_keys=("query",),
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
    independent_review_complete = (
        len(qrel_provenance["reviewer_ids"]) > 1
        and len(claim_provenance["reviewer_ids"]) > 1
    )
    partition = _partition_report(cases)

    review_queue = []
    if not independent_review_complete:
        review_queue.append(
            {
                "issue_id": "independent-review-required",
                "status": "review-required",
                "affected_population": "truth-set",
                "reason": "qrels and claim truth each have only one primary reviewer",
            }
        )
    for population in ("query", "qrel", "claim"):
        overlap_count = partition["overlap"][f"{population}_count"]
        if overlap_count:
            review_queue.append(
                {
                    "issue_id": f"{population}-split-leakage",
                    "status": "replacement-required",
                    "affected_population": population,
                    "overlap_count": overlap_count,
                    "reason": (
                        f"{population} identities occur in development and held-out rows"
                    ),
                }
            )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "inventory": {
            "case_row_count": len(cases),
            "unique_case_count": len(case_ids),
            "unique_claim_count": len(claim_ids),
            "unique_claim_identity_count": len(claim_identities),
            "unique_qrel_claim_pair_count": len(pairs),
            "unique_qrel_count": len(qrel_ids),
            "unique_query_count": len(query_ids),
            "unique_query_text_count": len(query_texts),
            "source_count": len(source_ids),
        },
        "query_inventory": query_rows,
        "qrel_inventory": qrel_inventory,
        "qrel_relevance_grade_counts": dict(
            sorted(Counter(str(record["relevance_grade"]) for record in qrels).items())
        ),
        "claim_inventory": claim_inventory,
        "claim_class_counts": dict(
            sorted(Counter(str(record["claim_class"]) for record in claims).items())
        ),
        "claim_verdict_counts": dict(
            sorted(Counter(str(record["verdict"]) for record in claims).items())
        ),
        "case_answerability_counts": dict(
            sorted(Counter(str(record["answerability"]) for record in cases).items())
        ),
        "case_label_counts": {
            "citation_relation": dict(
                sorted(
                    Counter(
                        str(record["labels"]["citation_relation"]) for record in cases
                    ).items()
                )
            ),
            "difficulty": dict(
                sorted(Counter(str(record["difficulty"]) for record in cases).items())
            ),
            "negative": dict(
                sorted(
                    Counter(
                        str(bool(record["labels"]["negative"])).lower()
                        for record in cases
                    ).items()
                )
            ),
            "split": dict(
                sorted(Counter(str(record["split"]) for record in cases).items())
            ),
        },
        "source_cross_products": source_cross_products,
        "dataset_consistency": consistency,
        "duplicates": duplicates,
        "contradictions": contradictions,
        "review_provenance": {
            "qrels": qrel_provenance,
            "claims": claim_provenance,
            "split": {
                "reviewer_ids": [str(split["reviewer_id"])],
                "reviewed_on": [str(split["reviewed_on"])],
                "review_methods": [str(split["review_method"])],
                "system_output_may_define_truth": bool(
                    split["partition_policy"]["system_output_may_define_truth"]
                ),
            },
            "independent_review_complete": independent_review_complete,
            "label_status": (
                "independently-reviewed"
                if independent_review_complete
                else "primary-reviewed-independent-review-required"
            ),
        },
        "partition": partition,
        "review_queue": review_queue,
        "release_eligible": not (
            any(duplicates.values())
            or any(contradictions.values())
            or not all(consistency.values())
            or review_queue
            or not partition["leakage_free"]
        ),
    }
    report["audit_identity_sha256"] = sha256(canonical(report))
    return report


def main() -> None:
    """Print the stable semantic-population audit."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--claim-truth", type=Path, required=True)
    parser.add_argument("--qrels", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    args = parser.parse_args()
    json.dump(
        audit_research_truth(
            cases_path=args.cases,
            claim_truth_path=args.claim_truth,
            qrels_path=args.qrels,
            split_path=args.split,
        ),
        sys.stdout,
        indent=2,
        sort_keys=True,
    )
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
