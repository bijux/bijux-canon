#!/usr/bin/env python3
"""Materialize a reviewed full-text JATS portfolio from acquisition receipts."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any
import xml.etree.ElementTree as ET

from bijux_canon_dev.corpus.acquisition import canonical, validate_jats

XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
MINIMUM_ABSTRACT_CHARACTERS = 100
MINIMUM_BODY_CHARACTERS = 1_000
MINIMUM_BODY_PARAGRAPHS = 5


def sha256(data: bytes) -> str:
    """Return a lowercase SHA-256 digest."""

    return hashlib.sha256(data).hexdigest()


def local_name(tag: str) -> str:
    """Return an XML local name with any namespace removed."""

    return tag.rsplit("}", 1)[-1]


def text_content(element: ET.Element) -> str:
    """Return normalized descendant text."""

    return " ".join("".join(element.itertext()).split())


def elements(root: ET.Element, name: str) -> list[ET.Element]:
    """Select descendants by namespace-independent local name."""

    return [element for element in root.iter() if local_name(element.tag) == name]


def children(root: ET.Element, name: str) -> list[ET.Element]:
    """Select direct children by namespace-independent local name."""

    return [element for element in root if local_name(element.tag) == name]


def supplementary_links(root: ET.Element) -> list[str]:
    """Return sorted distinct links declared by supplementary JATS elements."""

    links: set[str] = set()
    for element in root.iter():
        if local_name(element.tag) not in {
            "supplementary-material",
            "media",
            "related-object",
        }:
            continue
        href = element.attrib.get(XLINK_HREF) or element.attrib.get("href")
        if href:
            links.add(href)
    return sorted(links)


def inspect_full_text(body: bytes, *, doi: str) -> dict[str, Any]:
    """Validate and summarize one complete JATS article."""

    validate_jats(body, doi=doi)
    root = ET.fromstring(body)
    fronts = children(root, "front")
    if len(fronts) != 1:
        raise ValueError("JATS article must contain exactly one front matter block")
    article_metadata = children(fronts[0], "article-meta")
    if len(article_metadata) != 1:
        raise ValueError("JATS article must contain exactly one article metadata block")
    bodies = children(root, "body")
    if len(bodies) != 1:
        raise ValueError("JATS article must contain exactly one body")
    abstracts = elements(article_metadata[0], "abstract")
    abstract_text = " ".join(text_content(element) for element in abstracts).strip()
    body_text = text_content(bodies[0])
    paragraphs = elements(bodies[0], "p")
    sections = elements(bodies[0], "sec")
    if len(abstract_text) < MINIMUM_ABSTRACT_CHARACTERS:
        raise ValueError("JATS article has no substantive abstract")
    if len(body_text) < MINIMUM_BODY_CHARACTERS:
        raise ValueError("JATS article is abstract-only or lacks substantive full text")
    if len(paragraphs) < MINIMUM_BODY_PARAGRAPHS or not sections:
        raise ValueError("JATS article lacks full-text paragraph or section structure")
    article_titles = elements(article_metadata[0], "article-title")
    if len(article_titles) != 1 or not text_content(article_titles[0]):
        raise ValueError("JATS article has no unique title")
    return {
        "article_type": root.attrib.get("article-type"),
        "article_title": text_content(article_titles[0]),
        "abstract_characters": len(abstract_text),
        "body_characters": len(body_text),
        "body_paragraphs": len(paragraphs),
        "body_sections": len(sections),
        "supplementary_links": supplementary_links(root),
    }


def write_exact(path: Path, body: bytes) -> None:
    """Write exact bytes once and reject any later replacement."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != body:
            raise RuntimeError(f"refusing to replace materialized source: {path}")
        return
    path.write_bytes(body)


def materialize_record(
    record: Mapping[str, Any],
    receipt: Mapping[str, Any],
    *,
    acquisition_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    """Validate one receipt and preserve its exact JATS bytes durably."""

    if receipt["source_id"] != record["source_id"]:
        raise ValueError("acquisition receipt source identity mismatch")
    if receipt["source_record_identity_sha256"] != record["record_identity_sha256"]:
        raise ValueError("acquisition receipt source-review identity mismatch")
    acquired_path = acquisition_root / receipt["local_path"]
    body = acquired_path.read_bytes()
    if len(body) != receipt["byte_count"] or sha256(body) != receipt["sha256"]:
        raise ValueError("acquired source bytes do not match their receipt")
    inspection = inspect_full_text(body, doi=record["doi"])
    target = output_root / "sources" / f"{record['source_id']}.xml"
    write_exact(target, body)
    return {
        "source_id": record["source_id"],
        "doi": record["doi"],
        "title": record["title"],
        "authors": record["authors"],
        "journal": record["journal"],
        "publication_year": record["publication_year"],
        "source_record_identity_sha256": record["record_identity_sha256"],
        "acquisition_receipt_identity_sha256": receipt["receipt_identity_sha256"],
        "media_type": receipt["media_type"],
        "byte_count": len(body),
        "sha256": sha256(body),
        "local_path": target.relative_to(output_root).as_posix(),
        "license": record["license"],
        "attribution": record["attribution"],
        "transformations": [],
        "inspection": inspection,
        "limitations": [
            "Supplementary links are inventoried but supplementary bytes are not acquired.",
            "Materialization proves full-text structure and byte identity, not scientific truth or corpus admission.",
        ],
    }


def build_manifest(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the deterministic durable portfolio manifest."""

    ordered = sorted(records, key=lambda item: item["source_id"])
    identity_rows = [
        {
            "source_id": item["source_id"],
            "source_record_identity_sha256": item["source_record_identity_sha256"],
            "acquisition_receipt_identity_sha256": item[
                "acquisition_receipt_identity_sha256"
            ],
            "sha256": item["sha256"],
        }
        for item in ordered
    ]
    return {
        "schema_version": "bijux.canon.full_text_jats_portfolio.v1",
        "state": "materialized",
        "source_count": len(ordered),
        "portfolio_identity_sha256": sha256(canonical(identity_rows)),
        "sources": ordered,
        "limitations": [
            "The portfolio contains exact reviewed JATS article bytes only.",
            "Truth labels, retrieval judgments, and held-out split assignments are separate governed outputs.",
        ],
    }


def build_evidence(
    *,
    repo: Path,
    manifest: Mapping[str, Any],
    graph: Mapping[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    """Build aggregate and unit-scoped evidence for CORPUS-004."""

    units = {
        unit["matrix_key"]["source_id"]: unit
        for unit in graph["units"]
        if unit["task_id"] == "CORPUS-004"
    }
    if manifest["source_count"] != 8 or set(units) != {
        item["source_id"] for item in manifest["sources"]
    }:
        raise RuntimeError("CORPUS-004 requires exactly eight graph-backed sources")
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    unit_results = [
        {
            "unit_id": units[item["source_id"]]["unit_id"],
            "source_id": item["source_id"],
            "format_id": units[item["source_id"]]["matrix_key"].get("format_id"),
            "status": "passed",
            "disposition": "verified_complete",
            "content_sha256": item["sha256"],
        }
        for item in manifest["sources"]
    ]
    return {
        "schema_version": "bijux.canon.production_finalization.corpus_materialization.v1",
        "task_id": "CORPUS-004",
        "task_status": "in_progress",
        "source_commit": source_commit,
        "result": "passed",
        "disposition": "verified_complete",
        "required_rows": 8,
        "verified_rows": len(unit_results),
        "portfolio_identity_sha256": manifest["portfolio_identity_sha256"],
        "manifest_path": str((output_root / "corpus-manifest.json").relative_to(repo)),
        "manifest_sha256": sha256(canonical(manifest)),
        "materializer_sha256": sha256(Path(__file__).read_bytes()),
        "unit_results": unit_results,
        "measurements": {
            "total_bytes": sum(item["byte_count"] for item in manifest["sources"]),
            "minimum_body_characters": min(
                item["inspection"]["body_characters"] for item in manifest["sources"]
            ),
            "minimum_body_paragraphs": min(
                item["inspection"]["body_paragraphs"] for item in manifest["sources"]
            ),
            "supplementary_link_count": sum(
                len(item["inspection"]["supplementary_links"])
                for item in manifest["sources"]
            ),
        },
    }


def write_unit_evidence(
    evidence: Mapping[str, Any],
    *,
    manifest: Mapping[str, Any],
    graph: Mapping[str, Any],
    unit_root: Path,
) -> None:
    """Write one generic evidence envelope per portfolio source."""

    units = {
        unit["unit_id"]: unit
        for unit in graph["units"]
        if unit["task_id"] == "CORPUS-004"
    }
    records = {item["source_id"]: item for item in manifest["sources"]}
    for result in evidence["unit_results"]:
        unit = units[result["unit_id"]]
        token = sha256(unit["unit_id"].encode())[:16]
        path = unit_root / token / "corpus-materialization.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        value = {
            "schema_version": "bijux.canon.production_finalization.corpus_materialization_unit.v1",
            "task_id": "CORPUS-004",
            "unit_id": unit["unit_id"],
            "source_commit": evidence["source_commit"],
            "row_sha256": unit["row_sha256"],
            "disposition": "verified_complete",
            "portfolio_identity_sha256": evidence["portfolio_identity_sha256"],
            "record": records[result["source_id"]],
            "unit_results": [result],
        }
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--acquisition-root", type=Path, required=True)
    parser.add_argument("--receipt-root", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--unit-root", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo.resolve(strict=True)
    review = json.loads(args.review.resolve(strict=True).read_text())
    graph = json.loads(args.graph.resolve(strict=True).read_text())
    review_records = sorted(review["records"], key=lambda item: item["source_id"])
    materialized = [
        materialize_record(
            record,
            json.loads((args.receipt_root / f"{record['source_id']}.json").read_text()),
            acquisition_root=args.acquisition_root.resolve(strict=True),
            output_root=args.output_root.resolve(),
        )
        for record in review_records
    ]
    manifest = build_manifest(materialized)
    if manifest["source_count"] != 8:
        raise RuntimeError("full-text portfolio is incomplete")
    manifest_path = args.output_root / "corpus-manifest.json"
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()
    if manifest_path.exists() and manifest_path.read_bytes() != manifest_bytes:
        raise RuntimeError("refusing to replace a different corpus manifest")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(manifest_bytes)

    evidence = build_evidence(
        repo=repo,
        manifest=manifest,
        graph=graph,
        output_root=args.output_root.resolve(),
    )
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    write_unit_evidence(
        evidence,
        manifest=manifest,
        graph=graph,
        unit_root=args.unit_root.resolve(),
    )
    print(
        json.dumps(
            {
                "portfolio_identity_sha256": manifest["portfolio_identity_sha256"],
                "source_count": manifest["source_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print(f"corpus materialization failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
