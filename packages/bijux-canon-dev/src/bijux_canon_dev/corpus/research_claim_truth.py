#!/usr/bin/env python3
"""Validate atomic research claims and exact citation relations."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any, Mapping

from bijux_canon_dev.corpus.acquisition import canonical, sha256
from bijux_canon_dev.corpus.research_qrels import (
    load_qrels,
    validate_qrels,
)


SCHEMA_VERSION = "bijux.canon.research_claim_truth.v1"
REVIEWER_ID = "bijux-corpus-curation-primary"
REVIEW_METHOD = "manual source-first atomic claim and citation adjudication"
CLASS_POLICY = {
    "expected": {
        "abstention_expected": False,
        "evidence_relation": "supports",
        "expected_in_answer": True,
        "verdict": "supported",
    },
    "optional": {
        "abstention_expected": False,
        "evidence_relation": "supports",
        "expected_in_answer": False,
        "verdict": "supported",
    },
    "opposed": {
        "abstention_expected": True,
        "evidence_relation": "opposes",
        "expected_in_answer": False,
        "verdict": "opposed",
    },
    "forbidden": {
        "abstention_expected": True,
        "evidence_relation": "limits",
        "expected_in_answer": False,
        "verdict": "forbidden",
    },
}


def claim_identity(record: Mapping[str, Any]) -> str:
    """Return the canonical identity of one claim-truth record."""

    core = {
        key: value for key, value in record.items() if key != "claim_identity_sha256"
    }
    return sha256(canonical(core))


def load_claim_truth(path: Path) -> list[dict[str, Any]]:
    """Load canonical claim truth from a regular, non-symlink JSONL file."""

    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"research claim truth is not a regular file: {path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_bytes().splitlines(), 1):
        if not line:
            raise RuntimeError(f"blank research claim truth line: {line_number}")
        value = json.loads(line)
        if not isinstance(value, dict) or canonical(value) != line:
            raise RuntimeError(
                f"non-canonical research claim truth line: {line_number}"
            )
        records.append(value)
    return records


def _validate_evidence(
    evidence: Mapping[str, Any],
    *,
    source_id: str,
    qrels: Mapping[str, Mapping[str, Any]],
) -> None:
    qrel_id = evidence.get("qrel_id")
    qrel = qrels.get(qrel_id) if isinstance(qrel_id, str) else None
    if qrel is None or qrel["source_id"] != source_id:
        raise RuntimeError(f"unknown research claim qrel: {qrel_id}")
    chunk = qrel["chunk"]
    required = {
        "chunk_id": chunk["chunk_id"],
        "chunk_index": chunk["chunk_index"],
        "source_sha256": qrel["source_sha256"],
    }
    drift = [key for key, expected in required.items() if evidence.get(key) != expected]
    if drift:
        raise RuntimeError(f"research claim evidence lineage drift: {drift}")
    start = evidence.get("character_start")
    end = evidence.get("character_end")
    text = evidence.get("exact_text")
    chunk_text = chunk["normalized_text"]
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 0
        or end <= start
        or end > len(chunk_text)
        or not isinstance(text, str)
        or not text
        or chunk_text[start:end] != text
        or evidence.get("exact_text_sha256") != sha256(text.encode())
    ):
        raise RuntimeError("research claim exact evidence mismatch")


def validate_claim_truth(
    records: list[dict[str, Any]],
    *,
    claim_truth_path: Path,
    lock_path: Path,
    locator_truth_path: Path,
    qrels_path: Path,
    research_root: Path,
) -> dict[str, Any]:
    """Validate claim classes, abstention policy, and exact evidence spans."""

    if claim_truth_path.is_symlink() or not claim_truth_path.is_file():
        raise RuntimeError("research claim truth must be a regular file")
    qrel_records = load_qrels(qrels_path.resolve(strict=True))
    qrel_result = validate_qrels(
        qrel_records,
        lock_path=lock_path,
        locator_truth_path=locator_truth_path,
        research_root=research_root,
    )
    qrels = {record["qrel_id"]: record for record in qrel_records}
    sources = {record["source_id"] for record in qrel_records}
    observed: dict[str, set[str]] = {source_id: set() for source_id in sources}
    truth_ids: set[str] = set()
    claim_texts: set[str] = set()

    for record in records:
        source_id = record.get("source_id")
        claim_class = record.get("claim_class")
        if not isinstance(source_id, str) or source_id not in sources:
            raise RuntimeError(f"unknown research claim source: {source_id}")
        if not isinstance(claim_class, str) or claim_class not in CLASS_POLICY:
            raise RuntimeError(f"invalid research claim class: {claim_class}")
        source_qrels = [qrel for qrel in qrel_records if qrel["source_id"] == source_id]
        source = source_qrels[0]
        required = {
            "schema_version": SCHEMA_VERSION,
            "source_sha256": source["source_sha256"],
            "lock_identity_sha256": source["lock_identity_sha256"],
            "qrel_set_sha256": qrel_result["qrel_set_sha256"],
            "reviewer_id": REVIEWER_ID,
            "review_method": REVIEW_METHOD,
            **CLASS_POLICY[claim_class],
        }
        drift = [
            key for key, expected in required.items() if record.get(key) != expected
        ]
        if drift:
            raise RuntimeError(
                f"research claim metadata drift for {source_id}: {drift}"
            )
        truth_id = record.get("truth_id")
        claim = record.get("claim")
        rationale = record.get("rationale")
        if (
            truth_id != f"{source_id}::claim::{claim_class}"
            or truth_id in truth_ids
            or claim_class in observed[source_id]
            or not isinstance(claim, str)
            or len(claim) < 20
            or claim in claim_texts
            or not isinstance(rationale, str)
            or len(rationale) < 40
        ):
            raise RuntimeError(f"invalid research claim judgment: {truth_id}")
        truth_ids.add(str(truth_id))
        claim_texts.add(claim)
        observed[source_id].add(claim_class)
        try:
            date.fromisoformat(record["reviewed_on"])
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError(
                f"invalid research claim review date: {truth_id}"
            ) from error
        evidence = record.get("evidence")
        if not isinstance(evidence, dict):
            raise RuntimeError(f"research claim evidence is not an object: {truth_id}")
        _validate_evidence(evidence, source_id=source_id, qrels=qrels)
        if record.get("claim_identity_sha256") != claim_identity(record):
            raise RuntimeError(f"research claim identity mismatch: {truth_id}")

    required_classes = set(CLASS_POLICY)
    if set(observed) != sources or any(
        classes != required_classes for classes in observed.values()
    ):
        raise RuntimeError("research claim class coverage mismatch")
    return {
        "claim_count": len(records),
        "claim_set_sha256": sha256(
            b"".join(canonical(record) + b"\n" for record in records)
        ),
        "qrel_set_sha256": qrel_result["qrel_set_sha256"],
        "source_count": len(sources),
    }


def main() -> None:
    """Validate the durable research claim and citation truth."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--claim-truth", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--locator-truth", type=Path, required=True)
    parser.add_argument("--qrels", type=Path, required=True)
    parser.add_argument("--research-root", type=Path, required=True)
    args = parser.parse_args()
    result = validate_claim_truth(
        load_claim_truth(args.claim_truth),
        claim_truth_path=args.claim_truth,
        lock_path=args.lock,
        locator_truth_path=args.locator_truth,
        qrels_path=args.qrels,
        research_root=args.research_root,
    )
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
