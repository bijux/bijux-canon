#!/usr/bin/env python3
"""Build and verify the immutable parser-source checksum lock."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

from bijux_canon_dev.corpus.parser_sources import (
    EXTENSIONS,
    canonical,
    load_portfolio,
    sha256,
    validate_media,
    validate_receipt_identity,
    write_exclusive,
)


def read_json(path: Path) -> dict[str, Any]:
    """Read one JSON object from a regular, non-symlink file."""

    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"parser lock input is not a regular file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"parser lock input is not a JSON object: {path}")
    return value


def validate_retrieval_time(value: str) -> None:
    """Require an explicit UTC RFC 3339 acquisition timestamp."""

    if not value.endswith("Z"):
        raise RuntimeError("parser source retrieval time is not explicit UTC")
    parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    if parsed.tzinfo != UTC:
        raise RuntimeError("parser source retrieval time is not UTC")


def validate_lock_document(document: Mapping[str, Any]) -> None:
    """Validate aggregate lock identity and declared totals."""

    if document.get("schema_version") != "bijux.canon.parser_source_lock.v1":
        raise RuntimeError("parser source lock schema mismatch")
    identity = document.get("lock_identity_sha256")
    core = {
        key: value for key, value in document.items() if key != "lock_identity_sha256"
    }
    if identity != sha256(canonical(core)):
        raise RuntimeError("parser source lock identity mismatch")
    sources = document.get("sources")
    if not isinstance(sources, list) or document.get("source_count") != len(sources):
        raise RuntimeError("parser source lock count mismatch")
    if document.get("total_bytes") != sum(source["byte_count"] for source in sources):
        raise RuntimeError("parser source lock byte total mismatch")
    identities = [source["parser_source_id"] for source in sources]
    if len(identities) != len(set(identities)):
        raise RuntimeError("parser source lock contains duplicate identities")


def locked_source(record: Mapping[str, Any], *, output_root: Path) -> dict[str, Any]:
    """Validate and lock one acquired parser source."""

    source_id = record["parser_source_id"]
    extension = EXTENSIONS[record["format_id"]]
    source_relative = Path("sources") / f"{source_id}.json"
    receipt_relative = Path("acquisition-receipts") / f"{source_id}.json"
    media_relative = Path("corpus") / f"{source_id}{extension}"
    source_path = output_root / source_relative
    receipt_path = output_root / receipt_relative
    media_path = output_root / media_relative
    if media_path.is_symlink() or not media_path.is_file():
        raise RuntimeError(f"parser media is not a regular file: {source_id}")

    source = read_json(source_path)
    source_identity = sha256(canonical(dict(record)))
    expected_source = {**record, "record_identity_sha256": source_identity}
    if (
        source != expected_source
        or source_path.read_bytes() != canonical(source) + b"\n"
    ):
        raise RuntimeError(f"parser source record identity mismatch: {source_id}")

    receipt = read_json(receipt_path)
    validate_receipt_identity(receipt)
    validate_retrieval_time(receipt["retrieved_at"])
    body = media_path.read_bytes()
    inspection = validate_media(record, body)
    expected_receipt_fields = {
        "parser_source_id": source_id,
        "format_id": record["format_id"],
        "source_record_identity_sha256": source_identity,
        "state": "acquired",
        "local_path": media_relative.as_posix(),
        "byte_count": len(body),
        "sha256": sha256(body),
        "license": record["license"],
        "attribution": record["attribution"],
        "redistribution": record["redistribution"],
        "transformations": record["transformations"],
        "inspection": inspection,
    }
    drift = [
        key
        for key, expected in expected_receipt_fields.items()
        if receipt.get(key) != expected
    ]
    if drift:
        raise RuntimeError(f"parser acquisition receipt drift for {source_id}: {drift}")
    if not record["redistribution"]["permitted"]:
        raise RuntimeError(f"parser source is not redistributable: {source_id}")
    if receipt["license_evidence"]["uri"] != record["license"]["evidence_uri"]:
        raise RuntimeError(f"parser license evidence URI drift: {source_id}")
    transport = receipt["transport"]
    if (
        transport["status"] != 200
        or transport["request_url"] != record["acquisition"]["request_url"]
        or transport["content_type"]
        not in record["acquisition"]["expected_media_types"]
        or receipt["media_type"] != transport["content_type"]
    ):
        raise RuntimeError(f"parser transport receipt drift: {source_id}")
    if not record["transformations"] and (
        transport["response_byte_count"] != len(body)
        or transport["response_sha256"] != sha256(body)
    ):
        raise RuntimeError(
            f"untransformed parser media differs from transport: {source_id}"
        )
    if record["transformations"] == ["extract-licensed-plos-article-html-v1"]:
        lowered = body.lower()
        forbidden = (b"<script", b"<style", b"<iframe", b"<img", b"article-tabs")
        if any(marker in lowered for marker in forbidden):
            raise RuntimeError("transformed HTML retains excluded interface material")

    return {
        "parser_source_id": source_id,
        "format_id": record["format_id"],
        "expected_disposition": record["expected_disposition"],
        "canonical_uri": record["canonical_uri"],
        "source_record_uri": source_relative.as_posix(),
        "source_record_identity_sha256": source_identity,
        "acquisition_receipt_uri": receipt_relative.as_posix(),
        "acquisition_receipt_identity_sha256": receipt["receipt_identity_sha256"],
        "local_path": media_relative.as_posix(),
        "media_type": receipt["media_type"],
        "byte_count": len(body),
        "sha256": sha256(body),
        "license": record["license"],
        "license_evidence_sha256": receipt["license_evidence"]["sha256"],
        "attribution": record["attribution"],
        "retrieved_at": receipt["retrieved_at"],
        "redistribution": record["redistribution"],
        "transformations": record["transformations"],
        "transport_response_byte_count": transport["response_byte_count"],
        "transport_response_sha256": transport["response_sha256"],
        "inspection": inspection,
    }


def build_lock(*, portfolio_path: Path, output_root: Path) -> dict[str, Any]:
    """Build a complete lock from the reviewed portfolio and durable receipts."""

    portfolio_path = portfolio_path.resolve(strict=True)
    output_root = output_root.resolve(strict=True)
    records = load_portfolio(portfolio_path)
    sources = [locked_source(record, output_root=output_root) for record in records]
    core = {
        "schema_version": "bijux.canon.parser_source_lock.v1",
        "portfolio_uri": portfolio_path.relative_to(output_root).as_posix(),
        "portfolio_sha256": sha256(portfolio_path.read_bytes()),
        "source_count": len(sources),
        "total_bytes": sum(source["byte_count"] for source in sources),
        "sources": sources,
    }
    document = {**core, "lock_identity_sha256": sha256(canonical(core))}
    validate_lock_document(document)
    return document


def write_lock(path: Path, document: Mapping[str, Any]) -> None:
    """Write the lock once or verify an identical restart."""

    validate_lock_document(document)
    write_exclusive(path, canonical(document) + b"\n")


def main() -> None:
    """Build or validate the parser-source lock."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--portfolio", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    args = parser.parse_args()
    document = build_lock(
        portfolio_path=args.portfolio,
        output_root=args.output_root,
    )
    write_lock(args.lock, document)
    json.dump(
        {
            "lock_identity_sha256": document["lock_identity_sha256"],
            "source_count": document["source_count"],
            "total_bytes": document["total_bytes"],
        },
        sys.stdout,
        indent=2,
        sort_keys=True,
    )
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
