#!/usr/bin/env python3
"""Build and validate an offline research-corpus provenance lock."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any, Mapping

from bijux_canon_dev.corpus.acquisition import canonical, sha256, write_exclusive


SCHEMA_VERSION = "bijux.canon.research_corpus_lock.v1"
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def read_object(path: Path) -> dict[str, Any]:
    """Read a JSON object from a regular, non-symlink file."""

    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"corpus-lock input is not a regular file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"corpus-lock input is not a JSON object: {path}")
    return value


def validate_utc_timestamp(value: object) -> None:
    """Require an explicit RFC 3339 UTC timestamp."""

    if not isinstance(value, str) or not value.endswith("Z"):
        raise RuntimeError("corpus acquisition time is not explicit UTC")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as error:
        raise RuntimeError("corpus acquisition time is not RFC 3339") from error
    if parsed.tzinfo != UTC:
        raise RuntimeError("corpus acquisition time is not UTC")


def acquisition_receipt_identity(receipt: Mapping[str, Any]) -> str:
    """Return the immutable identity recorded by an acquisition receipt."""

    core = {
        key: value
        for key, value in receipt.items()
        if key not in {"retrieved_at", "transport", "receipt_identity_sha256"}
    }
    return sha256(canonical(core))


def validate_acquisition_receipt(receipt: Mapping[str, Any]) -> None:
    """Reject modified, incomplete, or non-checksummed acquisition receipts."""

    if receipt.get("schema_version") != "bijux.canon.corpus_acquisition_receipt.v1":
        raise RuntimeError("corpus acquisition receipt schema mismatch")
    if receipt.get("state") != "checksummed":
        raise RuntimeError("corpus acquisition receipt is not checksummed")
    validate_utc_timestamp(receipt.get("retrieved_at"))
    identity = receipt.get("receipt_identity_sha256")
    if identity != acquisition_receipt_identity(receipt):
        raise RuntimeError("corpus acquisition receipt identity mismatch")
    if SHA256.fullmatch(str(receipt.get("sha256", ""))) is None:
        raise RuntimeError("corpus acquisition receipt digest is invalid")
    transport = receipt.get("transport")
    if (
        not isinstance(transport, dict)
        or transport.get("status") != 200
        or transport.get("content_type") not in {"application/xml", "text/xml"}
    ):
        raise RuntimeError("corpus acquisition transport is not admitted JATS")


def lock_identity(document: Mapping[str, Any]) -> str:
    """Return the canonical identity of a corpus lock."""

    core = {
        key: value for key, value in document.items() if key != "lock_identity_sha256"
    }
    return sha256(canonical(core))


def _safe_source_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise RuntimeError(f"corpus lock contains an unsafe source path: {value}")
    return path


def validate_lock_document(
    document: Mapping[str, Any], *, research_root: Path | None = None
) -> None:
    """Validate aggregate identity, provenance fields, and optional local bytes."""

    if document.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("research corpus lock schema mismatch")
    if document.get("state") != "locked":
        raise RuntimeError("research corpus is not locked")
    if document.get("lock_identity_sha256") != lock_identity(document):
        raise RuntimeError("research corpus lock identity mismatch")
    sources = document.get("sources")
    if not isinstance(sources, list) or not sources:
        raise RuntimeError("research corpus lock has no sources")
    if document.get("source_count") != len(sources):
        raise RuntimeError("research corpus lock source count mismatch")
    if document.get("total_bytes") != sum(source["byte_count"] for source in sources):
        raise RuntimeError("research corpus lock byte total mismatch")
    source_ids = [source.get("source_id") for source in sources]
    if source_ids != sorted(source_ids) or len(source_ids) != len(set(source_ids)):
        raise RuntimeError("research corpus lock source identities are not unique and sorted")

    resolved_root = research_root.resolve(strict=True) if research_root else None
    for source in sources:
        for field in (
            "source_record_identity_sha256",
            "acquisition_receipt_identity_sha256",
            "sha256",
        ):
            if SHA256.fullmatch(str(source.get(field, ""))) is None:
                raise RuntimeError(f"research corpus lock digest is invalid: {field}")
        validate_utc_timestamp(source.get("retrieved_at"))
        if source.get("media_type") != "application/xml":
            raise RuntimeError("research corpus lock contains non-JATS media")
        redistribution = source.get("offline_redistribution")
        if (
            not isinstance(redistribution, dict)
            or redistribution.get("permitted") is not True
            or not redistribution.get("terms")
        ):
            raise RuntimeError("research corpus lock lacks offline redistribution terms")
        relative_path = _safe_source_path(source["local_path"])
        if resolved_root is not None:
            source_path = resolved_root.joinpath(*relative_path.parts)
            if source_path.is_symlink() or not source_path.is_file():
                raise RuntimeError(
                    f"research corpus source is not a regular file: {relative_path}"
                )
            body = source_path.read_bytes()
            if (
                len(body) != source["byte_count"]
                or sha256(body) != source["sha256"]
            ):
                raise RuntimeError(
                    f"research corpus source bytes drifted: {source['source_id']}"
                )


def _locked_source(
    manifest_source: Mapping[str, Any],
    *,
    corpus_root: Path,
    receipt_root: Path,
) -> dict[str, Any]:
    source_id = manifest_source["source_id"]
    receipt = read_object(receipt_root / f"{source_id}.json")
    validate_acquisition_receipt(receipt)
    manifest_path = _safe_source_path(manifest_source["local_path"])
    body_path = corpus_root.joinpath(*manifest_path.parts)
    if body_path.is_symlink() or not body_path.is_file():
        raise RuntimeError(f"research corpus source is not a regular file: {source_id}")
    body = body_path.read_bytes()

    matching_fields = (
        "source_id",
        "source_record_identity_sha256",
        "acquisition_receipt_identity_sha256",
        "doi",
        "title",
        "authors",
        "journal",
        "publication_year",
        "media_type",
        "byte_count",
        "sha256",
        "license",
        "attribution",
        "transformations",
    )
    expected = {
        **manifest_source,
        "acquisition_receipt_identity_sha256": receipt[
            "receipt_identity_sha256"
        ],
    }
    observed = {
        **receipt,
        "acquisition_receipt_identity_sha256": receipt[
            "receipt_identity_sha256"
        ],
    }
    drift = [
        field
        for field in matching_fields
        if expected.get(field) != observed.get(field)
    ]
    if (
        drift
        or len(body) != manifest_source["byte_count"]
        or sha256(body) != manifest_source["sha256"]
    ):
        raise RuntimeError(f"research corpus provenance drift for {source_id}: {drift}")

    transport = receipt["transport"]
    return {
        "source_id": source_id,
        "doi": manifest_source["doi"],
        "canonical_uri": f"https://doi.org/{manifest_source['doi']}",
        "title": manifest_source["title"],
        "authors": manifest_source["authors"],
        "journal": manifest_source["journal"],
        "publication_year": manifest_source["publication_year"],
        "source_record_identity_sha256": manifest_source[
            "source_record_identity_sha256"
        ],
        "acquisition_receipt_identity_sha256": receipt[
            "receipt_identity_sha256"
        ],
        "retrieved_at": receipt["retrieved_at"],
        "media_type": "application/xml",
        "byte_count": len(body),
        "sha256": sha256(body),
        "local_path": f"corpus/{manifest_path.as_posix()}",
        "license": manifest_source["license"],
        "attribution": manifest_source["attribution"],
        "transformations": manifest_source["transformations"],
        "offline_redistribution": {
            "permitted": True,
            "terms": receipt["redistribution_terms"],
            "access_terms": receipt["access_terms"],
        },
        "retrieval": {
            "request_url": transport["request_url"],
            "final_origin": transport["final_origin"],
            "final_path": transport["final_path"],
            "content_type": transport["content_type"],
            "etag": transport.get("etag"),
            "last_modified": transport.get("last_modified"),
        },
        "supplementary_links": manifest_source["inspection"][
            "supplementary_links"
        ],
        "limitations": manifest_source["limitations"],
    }


def build_lock(
    *,
    manifest_path: Path,
    corpus_root: Path,
    receipt_root: Path,
) -> dict[str, Any]:
    """Build a complete offline lock from materialized bytes and acquisition receipts."""

    manifest_path = manifest_path.resolve(strict=True)
    corpus_root = corpus_root.resolve(strict=True)
    receipt_root = receipt_root.resolve(strict=True)
    manifest = read_object(manifest_path)
    if (
        manifest.get("schema_version") != "bijux.canon.full_text_jats_portfolio.v1"
        or manifest.get("state") != "materialized"
        or manifest.get("source_count") != len(manifest.get("sources", []))
    ):
        raise RuntimeError("research corpus manifest is not materialized")
    sources = sorted(
        (
            _locked_source(
                source,
                corpus_root=corpus_root,
                receipt_root=receipt_root,
            )
            for source in manifest["sources"]
        ),
        key=lambda source: source["source_id"],
    )
    core = {
        "schema_version": SCHEMA_VERSION,
        "corpus_id": "ancient-dna-research",
        "state": "locked",
        "manifest_identity_sha256": manifest["portfolio_identity_sha256"],
        "manifest_sha256": sha256(manifest_path.read_bytes()),
        "source_count": len(sources),
        "total_bytes": sum(source["byte_count"] for source in sources),
        "sources": sources,
        "limitations": [
            "The lock admits exact article bytes for offline research use; supplementary bytes remain excluded.",
            "Scientific truth, evaluation splits, and claim judgments are governed separately.",
        ],
    }
    document = {**core, "lock_identity_sha256": sha256(canonical(core))}
    validate_lock_document(document)
    return document


def write_lock(path: Path, document: Mapping[str, Any]) -> None:
    """Write the lock once or verify an identical restart."""

    validate_lock_document(document)
    write_exclusive(path, canonical(document) + b"\n")


def main() -> None:
    """Build or replay the research-corpus lock."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--receipt-root", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    args = parser.parse_args()
    document = build_lock(
        manifest_path=args.manifest,
        corpus_root=args.corpus_root,
        receipt_root=args.receipt_root,
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
