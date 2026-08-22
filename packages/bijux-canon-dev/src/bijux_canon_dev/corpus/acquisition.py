#!/usr/bin/env python3
"""Acquire reviewed corpus media without weakening source identity."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import UTC, datetime
import hashlib
from http.client import HTTPMessage
import json
import os
from pathlib import Path
import ssl
import subprocess
import sys
import time
from typing import IO, Any, BinaryIO, cast
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

USER_AGENT = "bijux-canon-corpus-acquisition/1.0 (https://github.com/bijux/bijux-canon)"
READ_CHUNK_BYTES = 64 * 1024
MINIMUM_JATS_BYTES = 1_024


def canonical(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes."""

    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def sha256(data: bytes) -> str:
    """Return a lowercase SHA-256 digest."""

    return hashlib.sha256(data).hexdigest()


def utc_now() -> str:
    """Return an RFC 3339 UTC timestamp."""

    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def origin(url: str) -> str:
    """Return a normalized HTTPS origin."""

    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username is not None:
        raise ValueError(f"URL is not an unauthenticated HTTPS origin: {url}")
    return f"{parsed.scheme}://{parsed.netloc}"


def jats_media(record: Mapping[str, Any]) -> Mapping[str, Any]:
    """Select the single reviewed JATS media record."""

    admitted = record["retrieval_policy"]["admitted_media"]
    if admitted != ["jats"] or record["preferred_media"] != "jats":
        raise ValueError(f"source does not admit only JATS: {record['source_id']}")
    matches = [item for item in record["media"] if item["role"] == "jats_manuscript"]
    if len(matches) != 1 or matches[0]["media_type"] not in {
        "application/xml",
        "text/xml",
    }:
        raise ValueError(
            f"source has no unique reviewed JATS media: {record['source_id']}"
        )
    return cast(Mapping[str, Any], matches[0])


def validate_request_url(url: str, policy: Mapping[str, Any]) -> None:
    """Reject acquisition requests outside the reviewed origin set."""

    if origin(url) not in policy["approved_request_origins"]:
        raise ValueError(f"request origin is not approved: {url}")


def validate_redirect_url(url: str, *, doi: str, policy: Mapping[str, Any]) -> None:
    """Reject redirects outside the reviewed storage namespace."""

    parsed = urllib.parse.urlsplit(url)
    if origin(url) not in policy["approved_redirect_origins"]:
        raise ValueError(f"redirect origin is not approved: {url}")
    if not parsed.path.startswith(policy["approved_redirect_path_prefix"]):
        raise ValueError(f"redirect path is not approved: {url}")
    if policy[
        "redirect_requires_matching_doi_path"
    ] and f"/{doi}/" not in urllib.parse.unquote(parsed.path):
        raise ValueError(f"redirect path does not contain the reviewed DOI: {url}")


class PolicyRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Validate every redirect before urllib follows it."""

    def __init__(self, *, doi: str, policy: Mapping[str, Any]) -> None:
        super().__init__()
        self._doi = doi
        self._policy = policy
        self.redirects: list[str] = []

    def redirect_request(
        self,
        request: urllib.request.Request,
        file_pointer: IO[bytes],
        code: int,
        message: str,
        headers: HTTPMessage,
        new_url: str,
    ) -> urllib.request.Request | None:
        validate_redirect_url(new_url, doi=self._doi, policy=self._policy)
        self.redirects.append(new_url)
        return super().redirect_request(
            request, file_pointer, code, message, headers, new_url
        )


def read_bounded(
    response: BinaryIO, *, maximum_bytes: int, content_length: str | None
) -> bytes:
    """Read a response without exceeding the reviewed byte ceiling."""

    if content_length is not None:
        try:
            declared = int(content_length)
        except ValueError as error:
            raise ValueError("response has an invalid Content-Length") from error
        if declared < 0 or declared > maximum_bytes:
            raise ValueError(
                f"response Content-Length {declared} exceeds {maximum_bytes} bytes"
            )
    chunks: list[bytes] = []
    observed = 0
    while True:
        chunk = response.read(min(READ_CHUNK_BYTES, maximum_bytes - observed + 1))
        if not chunk:
            break
        observed += len(chunk)
        if observed > maximum_bytes:
            raise ValueError(f"response exceeds {maximum_bytes} bytes")
        chunks.append(chunk)
    return b"".join(chunks)


def validate_jats(body: bytes, *, doi: str) -> None:
    """Require a full JATS article whose front matter names the reviewed DOI."""

    if len(body) < MINIMUM_JATS_BYTES:
        raise ValueError("JATS response is implausibly small")
    try:
        root = ET.fromstring(body)
    except ET.ParseError as error:
        raise ValueError("JATS response is not well-formed XML") from error
    if root.tag.rsplit("}", 1)[-1] != "article":
        raise ValueError("XML response root is not a JATS article")
    observed_dois = {
        "".join(element.itertext()).strip().casefold()
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "article-id"
        and element.attrib.get("pub-id-type") == "doi"
    }
    if doi.casefold() not in observed_dois:
        raise ValueError(f"JATS article does not contain the reviewed DOI: {doi}")


def write_exclusive(path: Path, data: bytes) -> None:
    """Create a read-only file or verify that identical bytes already exist."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError(f"refusing to replace existing bytes: {path}")
        return
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        written = 0
        while written < len(data):
            written += os.write(descriptor, data[written:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def validate_existing_source(source_root: Path, expected_sha256: str) -> None:
    """Refuse a second byte identity for a stable source directory."""

    if not source_root.exists():
        return
    unexpected = [
        path
        for path in source_root.glob("*.xml")
        if path.name != f"{expected_sha256}.xml"
    ]
    if unexpected:
        raise RuntimeError(
            f"stable source already has different acquired bytes: {unexpected[0]}"
        )


def fetch_jats(record: Mapping[str, Any]) -> tuple[bytes, dict[str, Any]]:
    """Retrieve and validate one reviewed JATS article."""

    media = jats_media(record)
    request_url = media["transport"]["request_url"]
    policy = record["retrieval_policy"]
    validate_request_url(request_url, policy)
    request = urllib.request.Request(
        request_url,
        headers={"Accept": "application/xml,text/xml", "User-Agent": USER_AGENT},
    )
    redirects = PolicyRedirectHandler(doi=record["doi"], policy=policy)
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl.create_default_context()), redirects
    )
    started = time.monotonic()
    with opener.open(request, timeout=60) as response:
        final_url = response.geturl()
        final_origin = origin(final_url)
        if final_origin == origin(request_url):
            if redirects.redirects:
                raise RuntimeError("redirect audit disagrees with final request origin")
        else:
            validate_redirect_url(final_url, doi=record["doi"], policy=policy)
        content_type = response.headers.get_content_type()
        if content_type not in {"application/xml", "text/xml"}:
            raise ValueError(f"JATS response MIME is not XML: {content_type}")
        body = read_bounded(
            response,
            maximum_bytes=policy["maximum_response_bytes"],
            content_length=response.headers.get("Content-Length"),
        )
        transport = {
            "request_url": request_url,
            "redirects": redirects.redirects,
            "final_url": final_url,
            "final_origin": final_origin,
            "final_path": urllib.parse.urlsplit(final_url).path,
            "status": response.status,
            "content_type": content_type,
            "content_length_header": response.headers.get("Content-Length"),
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
            "duration_seconds": round(time.monotonic() - started, 6),
        }
    if transport["status"] != 200:
        raise RuntimeError(f"unexpected acquisition status: {transport['status']}")
    reviewed_transport = media["transport"]
    if (
        transport["final_origin"] != reviewed_transport["final_origin"]
        or transport["final_path"] != reviewed_transport["final_path"]
    ):
        raise RuntimeError("JATS endpoint changed since source review")
    validate_jats(body, doi=record["doi"])
    return body, transport


def acquisition_core(
    record: Mapping[str, Any],
    *,
    body: bytes,
    corpus_root: Path,
) -> dict[str, Any]:
    """Build the immutable portion of an acquisition receipt."""

    body_sha256 = sha256(body)
    relative_path = Path("objects") / record["source_id"] / f"{body_sha256}.xml"
    return {
        "schema_version": "bijux.canon.corpus_acquisition_receipt.v1",
        "source_id": record["source_id"],
        "source_record_identity_sha256": record["record_identity_sha256"],
        "state": "checksummed",
        "doi": record["doi"],
        "title": record["title"],
        "authors": record["authors"],
        "journal": record["journal"],
        "publication_year": record["publication_year"],
        "media_type": "application/xml",
        "byte_count": len(body),
        "sha256": body_sha256,
        "license": record["license"],
        "attribution": record["attribution"],
        "access_terms": record["access_terms"],
        "redistribution_terms": record["redistribution_terms"],
        "transformations": [],
        "local_path": relative_path.as_posix(),
        "corpus_root": str(corpus_root),
        "limitations": [
            "Acquired bytes are not parsed, truth-annotated, admitted, held out, or published by this receipt.",
            "Supplementary and separately credited third-party assets remain excluded.",
        ],
    }


def acquire_record(
    record: Mapping[str, Any],
    *,
    corpus_root: Path,
    receipt_root: Path,
    refresh: bool,
) -> dict[str, Any]:
    """Acquire or replay one immutable reviewed source."""

    receipt_path = receipt_root / f"{record['source_id']}.json"
    existing = json.loads(receipt_path.read_text()) if receipt_path.exists() else None
    if existing is not None and not refresh:
        if (
            existing["source_record_identity_sha256"]
            != record["record_identity_sha256"]
        ):
            raise RuntimeError("existing receipt belongs to a different source review")
        body_path = corpus_root / existing["local_path"]
        body = body_path.read_bytes()
        if len(body) != existing["byte_count"] or sha256(body) != existing["sha256"]:
            raise RuntimeError("existing acquired bytes do not match their receipt")
        validate_jats(body, doi=record["doi"])
        return cast(dict[str, Any], existing)

    body, transport = fetch_jats(record)
    core = acquisition_core(record, body=body, corpus_root=corpus_root)
    source_root = (corpus_root / core["local_path"]).parent
    validate_existing_source(source_root, core["sha256"])
    write_exclusive(corpus_root / core["local_path"], body)
    receipt = {
        **core,
        "retrieved_at": utc_now(),
        "transport": transport,
        "receipt_identity_sha256": sha256(canonical(core)),
    }
    if existing is not None:
        comparable_existing = {key: existing[key] for key in core}
        if comparable_existing != core:
            raise RuntimeError(
                "stable source returned bytes inconsistent with its receipt"
            )
        return cast(dict[str, Any], existing)
    write_exclusive(
        receipt_path,
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True).encode()
        + b"\n",
    )
    return receipt


def build_result(
    *,
    repo: Path,
    review: Mapping[str, Any],
    receipts: list[dict[str, Any]],
    graph: Mapping[str, Any],
    corpus_root: Path,
    receipt_root: Path,
    refresh: bool,
) -> dict[str, Any]:
    """Build aggregate and unit-scoped acquisition evidence."""

    units = {
        unit["matrix_key"]["source_id"]: unit
        for unit in graph["units"]
        if unit["task_id"] == "CORPUS-003"
    }
    if len(receipts) != 8 or set(units) != {item["source_id"] for item in receipts}:
        raise RuntimeError("CORPUS-003 requires all eight graph-backed sources")
    unit_results = [
        {
            "unit_id": units[receipt["source_id"]]["unit_id"],
            "source_id": receipt["source_id"],
            "format_id": units[receipt["source_id"]]["matrix_key"].get("format_id"),
            "status": "passed",
            "disposition": "verified_complete",
            "receipt_identity_sha256": receipt["receipt_identity_sha256"],
            "content_sha256": receipt["sha256"],
        }
        for receipt in receipts
    ]
    snapshot_identity = sha256(
        canonical(
            [
                {
                    "source_id": receipt["source_id"],
                    "source_record_identity_sha256": receipt[
                        "source_record_identity_sha256"
                    ],
                    "receipt_identity_sha256": receipt["receipt_identity_sha256"],
                    "content_sha256": receipt["sha256"],
                }
                for receipt in receipts
            ]
        )
    )
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    return {
        "schema_version": "bijux.canon.production_finalization.corpus_acquisition.v1",
        "task_id": "CORPUS-003",
        "task_status": "in_progress",
        "source_commit": source_commit,
        "result": "passed",
        "disposition": "verified_complete",
        "refresh_requested": refresh,
        "required_rows": 8,
        "verified_rows": len(receipts),
        "snapshot_identity_sha256": snapshot_identity,
        "source_review_identity_sha256": review["corpus_identity_sha256"],
        "corpus_root": str(corpus_root),
        "receipt_root": str(receipt_root),
        "unit_results": unit_results,
        "receipts": receipts,
        "governing_identities": {
            "acquisition_builder_path": str(Path(__file__).resolve().relative_to(repo)),
            "acquisition_builder_sha256": sha256(Path(__file__).read_bytes()),
            "source_review_sha256": sha256(canonical(review)),
        },
        "limitations": [
            "This acquisition does not parse or admit article content.",
            "The corpus object and receipt roots are disposable run products and remain untracked.",
        ],
    }


def write_unit_evidence(
    result: Mapping[str, Any], *, graph: Mapping[str, Any], unit_root: Path
) -> None:
    """Write one generic unit evidence envelope per acquired source."""

    units = {
        unit["unit_id"]: unit
        for unit in graph["units"]
        if unit["task_id"] == "CORPUS-003"
    }
    receipts = {item["source_id"]: item for item in result["receipts"]}
    for unit_result in result["unit_results"]:
        unit = units[unit_result["unit_id"]]
        token = sha256(unit["unit_id"].encode())[:16]
        path = unit_root / token / "corpus-acquisition.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        evidence = {
            "schema_version": "bijux.canon.production_finalization.corpus_acquisition_unit.v1",
            "task_id": "CORPUS-003",
            "unit_id": unit["unit_id"],
            "source_commit": result["source_commit"],
            "row_sha256": unit["row_sha256"],
            "disposition": "verified_complete",
            "snapshot_identity_sha256": result["snapshot_identity_sha256"],
            "receipt": receipts[unit_result["source_id"]],
            "unit_results": [unit_result],
        }
        path.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--receipt-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--unit-root", type=Path, required=True)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    repo = args.repo.resolve(strict=True)
    review = json.loads(args.review.resolve(strict=True).read_text())
    graph = json.loads(args.graph.resolve(strict=True).read_text())
    if review["task_id"] != "CORPUS-002" or review["result"] != "passed":
        raise RuntimeError("source review is not an admitted CORPUS-002 result")
    records = sorted(review["records"], key=lambda item: item["source_id"])
    receipts = [
        acquire_record(
            record,
            corpus_root=args.corpus_root.resolve(),
            receipt_root=args.receipt_root.resolve(),
            refresh=args.refresh,
        )
        for record in records
    ]
    result = build_result(
        repo=repo,
        review=review,
        receipts=receipts,
        graph=graph,
        corpus_root=args.corpus_root.resolve(),
        receipt_root=args.receipt_root.resolve(),
        refresh=args.refresh,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    write_unit_evidence(result, graph=graph, unit_root=args.unit_root.resolve())
    print(
        json.dumps(
            {
                "snapshot_identity_sha256": result["snapshot_identity_sha256"],
                "verified_rows": result["verified_rows"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, urllib.error.URLError) as error:
        print(f"corpus acquisition failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
