#!/usr/bin/env python3
"""Admit the fully reviewed parser-qualification portfolio."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
from pathlib import Path
import re
import sys
from typing import Any

from bijux_canon_dev.corpus.parser_locator_truth import (
    load_truth,
    validate_truth,
)
from bijux_canon_dev.corpus.parser_lock import (
    build_lock,
    read_json,
    validate_lock_document,
)
from bijux_canon_dev.corpus.parser_sources import canonical, sha256, write_exclusive

SCHEMA_VERSION = "bijux.canon.parser_portfolio_admission.v1"
COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")


def admission_identity(document: Mapping[str, Any]) -> str:
    """Return the canonical identity of an admission document."""

    core = {
        key: value
        for key, value in document.items()
        if key != "admission_identity_sha256"
    }
    return sha256(canonical(core))


def validate_admission_document(document: Mapping[str, Any]) -> None:
    """Validate aggregate admission identity and declared counts."""

    if document.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("parser admission schema mismatch")
    if COMMIT_SHA.fullmatch(str(document.get("source_commit", ""))) is None:
        raise RuntimeError("parser admission source commit is not a full SHA")
    if document.get("portfolio_scope") != {
        "kind": "parser-qualification",
        "flagship_research_corpus": False,
        "scientific_claims_admitted": False,
    }:
        raise RuntimeError("parser admission scope drift")
    if document.get("checks") != {
        "source_receipts": "passed",
        "license_and_redistribution": "passed",
        "checksum_lock": "passed",
        "format_and_safety": "passed",
        "locator_truth": "passed",
    }:
        raise RuntimeError("parser admission checks are incomplete")
    if document.get("admission_identity_sha256") != admission_identity(document):
        raise RuntimeError("parser admission identity mismatch")
    sources = document.get("sources")
    if not isinstance(sources, list) or document.get("source_count") != len(sources):
        raise RuntimeError("parser admission source count mismatch")
    admitted = [source for source in sources if source.get("state") == "admitted"]
    if len(admitted) != len(sources):
        raise RuntimeError("parser admission contains a non-admitted source")
    parser_inputs = [
        source
        for source in sources
        if source.get("qualification_outcome") == "parser-input-admitted"
    ]
    refusals = [
        source
        for source in sources
        if source.get("qualification_outcome") == "ocr-required"
    ]
    if document.get("parser_input_count") != len(parser_inputs):
        raise RuntimeError("parser admission input count mismatch")
    if document.get("typed_refusal_count") != len(refusals):
        raise RuntimeError("parser admission refusal count mismatch")
    if len(parser_inputs) + len(refusals) != len(sources):
        raise RuntimeError("parser admission has an undeclared outcome")
    source_ids = [source.get("parser_source_id") for source in sources]
    if not all(isinstance(source_id, str) for source_id in source_ids) or len(
        source_ids
    ) != len(set(source_ids)):
        raise RuntimeError("parser admission has duplicate source identities")
    byte_counts = [source.get("byte_count") for source in sources]
    if not all(
        isinstance(byte_count, int) and not isinstance(byte_count, bool)
        for byte_count in byte_counts
    ) or document.get("total_bytes") != sum(byte_counts):
        raise RuntimeError("parser admission byte total mismatch")
    if not all(source.get("redistribution_permitted") is True for source in sources):
        raise RuntimeError("parser admission contains disallowed redistribution")


def build_admission(
    *,
    source_commit: str,
    portfolio_path: Path,
    output_root: Path,
    lock_path: Path,
    truth_path: Path,
) -> dict[str, Any]:
    """Revalidate every durable receipt and build a scoped admission record."""

    if COMMIT_SHA.fullmatch(source_commit) is None:
        raise RuntimeError("parser admission source commit is not a full SHA")
    output_root = output_root.resolve(strict=True)
    portfolio_path = portfolio_path.resolve(strict=True)
    lock_path = lock_path.resolve(strict=True)
    truth_path = truth_path.resolve(strict=True)
    lock = read_json(lock_path)
    validate_lock_document(lock)
    rebuilt_lock = build_lock(
        portfolio_path=portfolio_path,
        output_root=output_root,
    )
    if lock != rebuilt_lock or lock_path.read_bytes() != canonical(lock) + b"\n":
        raise RuntimeError("parser admission lock differs from durable source receipts")
    truth_records = load_truth(truth_path)
    truth_summary = validate_truth(
        truth_records,
        portfolio_path=portfolio_path,
        output_root=output_root,
        lock_path=lock_path,
    )
    truth_by_source: dict[str, list[dict[str, Any]]] = {}
    for record in truth_records:
        truth_by_source.setdefault(record["parser_source_id"], []).append(record)

    sources = []
    for locked in lock["sources"]:
        source_id = locked["parser_source_id"]
        truth = truth_by_source.get(source_id, [])
        if not truth:
            raise RuntimeError(f"parser admission has no locator truth: {source_id}")
        outcome = (
            "ocr-required"
            if locked["expected_disposition"] == "verified_ocr_refusal"
            else "parser-input-admitted"
        )
        sources.append(
            {
                "parser_source_id": source_id,
                "format_id": locked["format_id"],
                "state": "admitted",
                "qualification_outcome": outcome,
                "disposition": locked["expected_disposition"],
                "canonical_uri": locked["canonical_uri"],
                "source_record_identity_sha256": locked[
                    "source_record_identity_sha256"
                ],
                "acquisition_receipt_identity_sha256": locked[
                    "acquisition_receipt_identity_sha256"
                ],
                "media_type": locked["media_type"],
                "byte_count": locked["byte_count"],
                "sha256": locked["sha256"],
                "license_expression": locked["license"]["expression"],
                "license_url": locked["license"]["url"],
                "license_evidence_sha256": locked["license_evidence_sha256"],
                "redistribution_permitted": locked["redistribution"]["permitted"],
                "transformations": locked["transformations"],
                "safety_inspection": locked["inspection"],
                "truth_record_count": len(truth),
                "truth_identity_sha256": [
                    record["truth_identity_sha256"] for record in truth
                ],
                "truth_roles": [record["block_role"] for record in truth],
            }
        )
    core = {
        "schema_version": SCHEMA_VERSION,
        "task_id": "FORMATDATA-005",
        "source_commit": source_commit,
        "portfolio_scope": {
            "kind": "parser-qualification",
            "flagship_research_corpus": False,
            "scientific_claims_admitted": False,
        },
        "portfolio_sha256": lock["portfolio_sha256"],
        "lock_identity_sha256": lock["lock_identity_sha256"],
        "truth_set_sha256": truth_summary["truth_set_sha256"],
        "source_count": len(sources),
        "parser_input_count": sum(
            source["qualification_outcome"] == "parser-input-admitted"
            for source in sources
        ),
        "typed_refusal_count": sum(
            source["qualification_outcome"] == "ocr-required" for source in sources
        ),
        "total_bytes": lock["total_bytes"],
        "checks": {
            "source_receipts": "passed",
            "license_and_redistribution": "passed",
            "checksum_lock": "passed",
            "format_and_safety": "passed",
            "locator_truth": "passed",
        },
        "sources": sources,
    }
    document = {**core, "admission_identity_sha256": sha256(canonical(core))}
    validate_admission_document(document)
    return document


def write_admission(path: Path, document: Mapping[str, Any]) -> None:
    """Write the admission once or verify an identical current-head replay."""

    validate_admission_document(document)
    write_exclusive(path, canonical(document) + b"\n")


def main() -> None:
    """Build or replay the current parser-portfolio admission record."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--portfolio", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--truth", type=Path, required=True)
    parser.add_argument("--admission", type=Path, required=True)
    args = parser.parse_args()
    document = build_admission(
        source_commit=args.source_commit,
        portfolio_path=args.portfolio,
        output_root=args.output_root,
        lock_path=args.lock,
        truth_path=args.truth,
    )
    write_admission(args.admission, document)
    json.dump(
        {
            "admission_identity_sha256": document["admission_identity_sha256"],
            "parser_input_count": document["parser_input_count"],
            "source_count": document["source_count"],
            "typed_refusal_count": document["typed_refusal_count"],
        },
        sys.stdout,
        indent=2,
        sort_keys=True,
    )
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
