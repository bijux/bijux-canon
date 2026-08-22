#!/usr/bin/env python3
"""Validate the frozen development and held-out research evaluation split."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping
import json
from pathlib import Path
import sys
from typing import Any

from bijux_canon_dev.corpus.acquisition import canonical, sha256
from bijux_canon_dev.corpus.research_claim_truth import (
    load_claim_truth,
    validate_claim_truth,
)
from bijux_canon_dev.corpus.research_qrels import load_qrels, validate_qrels

SCHEMA_VERSION = "bijux.canon.research_evaluation_split.v1"
CASE_SCHEMA_VERSION = "bijux.canon.research_evaluation_case.v1"
REVIEWER_ID = "bijux-corpus-curation-primary"
REVIEW_STATUS = "primary_manual_review_complete"
REVIEW_METHOD = "manual review of qrel-by-claim evaluation case construction"
SPLIT_SEED = "bijux-canon-ancient-dna-development-heldout-v1"
CLAIM_CLASS_ORDER = {
    name: index
    for index, name in enumerate(("expected", "optional", "opposed", "forbidden"))
}


def split_identity(document: Mapping[str, Any]) -> str:
    """Return the canonical identity of a split document."""

    core = {
        key: value for key, value in document.items() if key != "split_identity_sha256"
    }
    return sha256(canonical(core))


def case_identity(record: Mapping[str, Any]) -> str:
    """Return the canonical identity of one evaluation case."""

    core = {
        key: value for key, value in record.items() if key != "case_identity_sha256"
    }
    return sha256(canonical(core))


def load_split(path: Path) -> dict[str, Any]:
    """Load a split document from a regular, non-symlink JSON file."""

    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"research evaluation split is not a regular file: {path}")
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise RuntimeError("research evaluation split is not an object")
    return value


def _relation(qrel: Mapping[str, Any], claim: Mapping[str, Any]) -> str:
    evidence = claim["evidence"]
    if evidence["exact_text"] not in qrel["chunk"]["normalized_text"]:
        return "insufficient"
    return str(claim["evidence_relation"])


def _difficulty(*, claim_class: str, relation: str, grade: int) -> str:
    if claim_class == "forbidden":
        return "adversarial"
    if claim_class == "opposed" or relation == "insufficient" or grade == 1:
        return "hard"
    return "standard"


def expected_case_labels(
    qrel: Mapping[str, Any], claim: Mapping[str, Any]
) -> dict[str, Any]:
    """Derive reviewed labels from exact qrel and claim/citation truth."""

    relation = _relation(qrel, claim)
    return {
        "abstention_expected": claim["abstention_expected"],
        "citation_relation": relation,
        "conflict": claim["claim_class"] == "opposed",
        "evidence_condition": {
            "supports": "answerable",
            "opposes": "opposed",
            "limits": "negative",
            "insufficient": "negative",
        }[relation],
        "negative": relation in {"limits", "insufficient"},
        "relevance_grade": qrel["relevance_grade"],
    }


def validate_split(
    document: dict[str, Any],
    *,
    claim_truth_path: Path,
    lock_path: Path,
    locator_truth_path: Path,
    qrels_path: Path,
    research_root: Path,
    split_path: Path,
) -> dict[str, Any]:
    """Validate all 120 truth combinations, strata, isolation, and hashes."""

    if split_path.is_symlink() or not split_path.is_file():
        raise RuntimeError("research evaluation split must be a regular file")
    qrel_records = load_qrels(qrels_path.resolve(strict=True))
    qrel_result = validate_qrels(
        qrel_records,
        lock_path=lock_path,
        locator_truth_path=locator_truth_path,
        research_root=research_root,
    )
    claim_records = load_claim_truth(claim_truth_path.resolve(strict=True))
    claim_result = validate_claim_truth(
        claim_records,
        claim_truth_path=claim_truth_path,
        lock_path=lock_path,
        locator_truth_path=locator_truth_path,
        qrels_path=qrels_path,
        research_root=research_root,
    )
    expected_policy = {
        "case_construction": "same-source graded-qrel-by-atomic-claim-cross-product",
        "development_case_count": 80,
        "heldout_case_count": 40,
        "heldout_labels_available_to_tuning": False,
        "heldout_per_claim_class": 10,
        "split_seed_sha256": sha256(SPLIT_SEED.encode()),
        "system_output_may_define_truth": False,
        "tuning_prohibited_uses": [
            "case-selection",
            "parameters",
            "prompts",
            "reranking",
            "thresholds",
        ],
    }
    required = {
        "schema_version": SCHEMA_VERSION,
        "qrel_set_sha256": qrel_result["qrel_set_sha256"],
        "claim_set_sha256": claim_result["claim_set_sha256"],
        "case_count": 120,
        "format_ids": ["jats"],
        "lock_identity_sha256": qrel_records[0]["lock_identity_sha256"],
        "review_method": REVIEW_METHOD,
        "reviewed_on": "2026-08-22",
        "reviewer_id": REVIEWER_ID,
        "review_status": REVIEW_STATUS,
        "partition_policy": expected_policy,
    }
    drift = [key for key, expected in required.items() if document.get(key) != expected]
    if drift:
        raise RuntimeError(f"research evaluation split metadata drift: {drift}")
    cases = document.get("cases")
    if not isinstance(cases, list) or len(cases) != 120:
        raise RuntimeError("research evaluation split must contain exactly 120 cases")
    qrels = {record["qrel_id"]: record for record in qrel_records}
    claims = {record["truth_id"]: record for record in claim_records}
    expected_pairs = {
        (qrel["qrel_id"], claim["truth_id"])
        for qrel in qrel_records
        for claim in claim_records
        if qrel["source_id"] == claim["source_id"]
    }
    observed_source_ids = {qrel["source_id"] for qrel in qrel_records}
    observed_pairs: set[tuple[str, str]] = set()
    case_ids: set[str] = set()
    split_counts: Counter[str] = Counter()
    heldout_classes: Counter[str] = Counter()
    heldout_sources: Counter[str] = Counter()
    strata: dict[str, set[Any]] = {
        "query_id": set(),
        "evidence_condition": set(),
        "conflict": set(),
        "negative": set(),
        "format_id": set(),
        "difficulty": set(),
    }
    for ordinal, case in enumerate(cases, 1):
        if not isinstance(case, dict):
            raise RuntimeError("research evaluation case is not an object")
        case_id = case.get("case_id")
        qrel_id = case.get("qrel_id")
        claim_id = case.get("claim_truth_id")
        qrel = qrels.get(qrel_id) if isinstance(qrel_id, str) else None
        claim = claims.get(claim_id) if isinstance(claim_id, str) else None
        if (
            case_id != f"adna-case-{ordinal:03d}"
            or case_id in case_ids
            or qrel is None
            or claim is None
            or qrel["source_id"] != claim["source_id"]
        ):
            raise RuntimeError(f"invalid research evaluation case binding: {case_id}")
        pair = (str(qrel_id), str(claim_id))
        if pair in observed_pairs:
            raise RuntimeError(f"duplicate research evaluation truth pair: {case_id}")
        observed_pairs.add(pair)
        case_ids.add(str(case_id))
        labels = expected_case_labels(qrel, claim)
        difficulty = _difficulty(
            claim_class=claim["claim_class"],
            relation=labels["citation_relation"],
            grade=qrel["relevance_grade"],
        )
        expected = {
            "schema_version": CASE_SCHEMA_VERSION,
            "source_id": qrel["source_id"],
            "query_id": qrel["query_id"],
            "claim_class": claim["claim_class"],
            "format_id": "jats",
            "difficulty": difficulty,
            "labels": labels,
            "reviewer_id": REVIEWER_ID,
            "review_status": REVIEW_STATUS,
            "system_output_may_define_truth": False,
        }
        case_drift = [
            key
            for key, expected_value in expected.items()
            if case.get(key) != expected_value
        ]
        split = case.get("split")
        if split not in {"development", "heldout"}:
            case_drift.append("split")
        if case_drift:
            raise RuntimeError(
                f"research evaluation case drift for {case_id}: {case_drift}"
            )
        split_counts[str(split)] += 1
        if split == "heldout":
            heldout_classes[claim["claim_class"]] += 1
            heldout_sources[qrel["source_id"]] += 1
        for name in strata:
            value = case[name] if name in case else labels[name]
            strata[name].add(value)
        if case.get("case_identity_sha256") != case_identity(case):
            raise RuntimeError(f"research evaluation case identity mismatch: {case_id}")
    if observed_pairs != expected_pairs:
        raise RuntimeError("research evaluation cross-product coverage mismatch")
    if split_counts != Counter({"development": 80, "heldout": 40}):
        raise RuntimeError("research evaluation partition count mismatch")
    if heldout_classes != Counter(dict.fromkeys(CLAIM_CLASS_ORDER, 10)):
        raise RuntimeError("research evaluation held-out class balance mismatch")
    if heldout_sources != Counter(dict.fromkeys(observed_source_ids, 5)):
        raise RuntimeError("research evaluation held-out source balance mismatch")
    expected_partitions = {
        split: [case["case_id"] for case in cases if case["split"] == split]
        for split in ("development", "heldout")
    }
    if document.get("partitions") != expected_partitions:
        raise RuntimeError("research evaluation partition index mismatch")
    required_strata = {
        "query_id": 8,
        "evidence_condition": 3,
        "conflict": 2,
        "negative": 2,
        "format_id": 1,
        "difficulty": 3,
    }
    if {name: len(values) for name, values in strata.items()} != required_strata:
        raise RuntimeError("research evaluation stratum coverage mismatch")
    case_set_sha256 = sha256(canonical(cases))
    if document.get("case_set_sha256") != case_set_sha256:
        raise RuntimeError("research evaluation case-set identity mismatch")
    if document.get("split_identity_sha256") != split_identity(document):
        raise RuntimeError("research evaluation split identity mismatch")
    return {
        "case_count": len(cases),
        "case_set_sha256": case_set_sha256,
        "development_case_count": split_counts["development"],
        "heldout_case_count": split_counts["heldout"],
        "source_count": len(strata["query_id"]),
        "split_identity_sha256": document["split_identity_sha256"],
    }


def main() -> None:
    """Validate the durable research evaluation partition."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--claim-truth", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--locator-truth", type=Path, required=True)
    parser.add_argument("--qrels", type=Path, required=True)
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    args = parser.parse_args()
    result = validate_split(
        load_split(args.split),
        claim_truth_path=args.claim_truth,
        lock_path=args.lock,
        locator_truth_path=args.locator_truth,
        qrels_path=args.qrels,
        research_root=args.research_root,
        split_path=args.split,
    )
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
