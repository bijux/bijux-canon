#!/usr/bin/env python3
"""Acquire and validate the heterogeneous parser qualification portfolio."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import UTC, datetime
import hashlib
from html import escape
from html.parser import HTMLParser
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import re
import ssl
import sys
import time
from typing import Any, BinaryIO, cast
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile


USER_AGENT = (
    "bijux-canon-parser-source-acquisition/1.0 "
    "(https://github.com/bijux/bijux-canon; bijan@bijux.io)"
)
READ_CHUNK_BYTES = 64 * 1024
EXTENSIONS = {
    "jats": ".xml",
    "pdf-digital": ".pdf",
    "html": ".html",
    "markdown": ".md",
    "text": ".txt",
    "docx": ".docx",
    "ocr-required": ".jpg",
}
LICENSE_MARKERS = {
    "CC-BY-4.0": ("Creative Commons Attribution", "4.0"),
    "Apache-2.0": ("Apache License", "Version 2.0"),
    "IETF-Trust-TLP-5.0": ("IETF Trust", "Legal Provisions", "March 25, 2015"),
    "OGL-UK-3.0": ("Open Government Licence v3.0",),
    "CC0-1.0": ("CC0 1.0 Universal",),
}


def canonical(value: Any) -> bytes:
    """Return canonical UTF-8 JSON bytes."""

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
    """Return a validated unauthenticated HTTPS origin."""

    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username is not None:
        raise ValueError(f"URL is not an unauthenticated HTTPS URL: {url}")
    return f"{parsed.scheme}://{parsed.netloc}"


def load_portfolio(path: Path) -> list[dict[str, Any]]:
    """Load the exact seven-row canonical parser-source policy."""

    text = path.read_text(encoding="utf-8")
    records = [json.loads(line) for line in text.splitlines() if line]
    if len(records) != 7:
        raise ValueError("parser portfolio must contain exactly seven sources")
    identities = [record["parser_source_id"] for record in records]
    formats = [record["format_id"] for record in records]
    if len(set(identities)) != len(records) or len(set(formats)) != len(records):
        raise ValueError("parser source and format identities must be unique")
    expected = set(EXTENSIONS)
    if set(formats) != expected:
        raise ValueError(f"parser portfolio format mismatch: {set(formats) ^ expected}")
    rendered = b"".join(canonical(record) + b"\n" for record in records)
    if rendered != text.encode():
        raise ValueError("parser portfolio is not canonical JSONL")
    for record in records:
        acquisition = record["acquisition"]
        if origin(acquisition["request_url"]) not in acquisition["approved_origins"]:
            raise ValueError("request URL is outside its approved origins")
        if not record["redistribution"]["permitted"]:
            raise ValueError("parser portfolio contains non-redistributable media")
        if record["license"]["expression"] not in LICENSE_MARKERS:
            raise ValueError("parser portfolio contains an unknown license expression")
    return records


def read_bounded(
    response: BinaryIO, *, maximum_bytes: int, content_length: str | None
) -> bytes:
    """Read a response while enforcing declared and observed byte ceilings."""

    if content_length is not None:
        try:
            declared = int(content_length)
        except ValueError as error:
            raise ValueError("response has an invalid Content-Length") from error
        if declared < 0 or declared > maximum_bytes:
            raise ValueError("response Content-Length exceeds the source policy")
    chunks: list[bytes] = []
    observed = 0
    while True:
        chunk = response.read(min(READ_CHUNK_BYTES, maximum_bytes - observed + 1))
        if not chunk:
            break
        observed += len(chunk)
        if observed > maximum_bytes:
            raise ValueError("response exceeds the source policy byte ceiling")
        chunks.append(chunk)
    return b"".join(chunks)


def open_with_retry(request: urllib.request.Request) -> Any:
    """Open an HTTPS request with a small bounded transient-error retry policy."""

    for attempt in range(3):
        try:
            return urllib.request.urlopen(
                request, timeout=90, context=ssl.create_default_context()
            )
        except urllib.error.HTTPError as error:
            if error.code not in {429, 503} or attempt == 2:
                raise
            retry_after = error.headers.get("Retry-After", "1")
            try:
                delay = min(max(float(retry_after), 0.0), 5.0)
            except ValueError:
                delay = 1.0
            time.sleep(delay)
    raise RuntimeError("unreachable retry state")


def fetch(record: Mapping[str, Any]) -> tuple[bytes, dict[str, Any]]:
    """Fetch one source and reject origin or media drift."""

    policy = record["acquisition"]
    request = urllib.request.Request(
        policy["request_url"],
        headers={
            "Accept": ",".join(policy["expected_media_types"]),
            "User-Agent": USER_AGENT,
        },
    )
    with open_with_retry(request) as response:
        final_url = response.geturl()
        if origin(final_url) not in policy["approved_origins"]:
            raise ValueError(f"redirect escaped approved origins: {final_url}")
        content_type = response.headers.get_content_type()
        if content_type not in policy["expected_media_types"]:
            raise ValueError(f"response media type is not admitted: {content_type}")
        body = read_bounded(
            response,
            maximum_bytes=policy["maximum_bytes"],
            content_length=response.headers.get("Content-Length"),
        )
        transport = {
            "request_url": policy["request_url"],
            "final_origin": origin(final_url),
            "final_path": urllib.parse.unquote(urllib.parse.urlsplit(final_url).path),
            "status": response.status,
            "content_type": content_type,
            "content_length_header": response.headers.get("Content-Length"),
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
            "response_byte_count": len(body),
            "response_sha256": sha256(body),
        }
    if transport["status"] != 200:
        raise ValueError(f"unexpected source status: {transport['status']}")
    return body, transport


def transform_html_article(body: bytes) -> bytes:
    """Retain licensed article HTML while removing publisher interface material."""

    text = body.decode("utf-8")
    metadata_parser = ArticleHTML()
    metadata_parser.feed(text)
    required_metadata = ("citation_title", "citation_author", "citation_doi")
    if any(not metadata_parser.metadata.get(name) for name in required_metadata):
        raise ValueError("HTML transport lacks required article metadata")
    match = re.search(
        r'<section\s+class="article-body">.*?\n\s*</section>', text, re.DOTALL
    )
    if match is None:
        raise ValueError("HTML transport lacks a bounded article-body region")
    article_body = match.group(0)
    article_body = re.sub(
        r'<ul\s+class="article-tabs">.*?</ul>',
        "",
        article_body,
        count=1,
        flags=re.DOTALL,
    )
    article_body = re.sub(
        r"<(?:script|style|template|iframe)\b.*?</(?:script|style|template|iframe)\s*>",
        "",
        article_body,
        flags=re.DOTALL | re.IGNORECASE,
    )
    article_body = re.sub(
        r"<(?:img|source)\b[^>]*>", "", article_body, flags=re.IGNORECASE
    )
    metadata = "\n".join(
        f'<meta name="{name}" content="{escape(value, quote=True)}">'
        for name in required_metadata
        for value in metadata_parser.metadata[name]
    )
    title = metadata_parser.metadata["citation_title"][0]
    transformed = (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        f"{metadata}\n<title>{escape(title)}</title>\n</head>\n<body>\n<main>\n"
        f"<article>\n<h1>{escape(title)}</h1>\n{article_body}\n</article>\n"
        "</main>\n</body>\n</html>\n"
    )
    return transformed.encode()


def apply_transformations(record: Mapping[str, Any], body: bytes) -> bytes:
    """Apply only the exact transformations declared by source policy."""

    transformations = record["transformations"]
    if not transformations:
        return body
    if transformations == ["extract-licensed-plos-article-html-v1"]:
        return transform_html_article(body)
    raise ValueError("parser source declares an unsupported transformation")


def fetch_license_evidence(record: Mapping[str, Any]) -> dict[str, Any]:
    """Verify that the cited page states the selected exact license."""

    url = record["license"]["evidence_uri"]
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with open_with_retry(request) as response:
        data = read_bounded(
            response,
            maximum_bytes=4 * 1024 * 1024,
            content_length=response.headers.get("Content-Length"),
        )
        status = response.status
    if status != 200:
        raise ValueError(f"unexpected license evidence status: {status}")
    text = data.decode("utf-8", errors="replace")
    markers = LICENSE_MARKERS[record["license"]["expression"]]
    if not all(marker.casefold() in text.casefold() for marker in markers):
        raise ValueError("license evidence does not state the selected license")
    return {"uri": url, "byte_count": len(data), "sha256": sha256(data)}


class ArticleHTML(HTMLParser):
    """Collect structural signals from a real article page."""

    def __init__(self) -> None:
        super().__init__()
        self.metadata: dict[str, list[str]] = {}
        self.article_elements = 0
        self.article_body_regions = 0
        self.main_elements = 0
        self.headings = 0
        self.paragraphs = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        name = attributes.get("name") or ""
        if tag == "meta" and name.startswith("citation_"):
            content = attributes.get("content")
            if content:
                self.metadata.setdefault(name, []).append(content)
        if tag == "article":
            self.article_elements += 1
        if tag == "main":
            self.main_elements += 1
        if "article-body" in (attributes.get("class") or "").split():
            self.article_body_regions += 1
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.headings += 1
        elif tag == "p":
            self.paragraphs += 1


def local_name(tag: str) -> str:
    """Return an XML local name."""

    return tag.rsplit("}", 1)[-1]


def jpeg_dimensions(data: bytes) -> tuple[int, int]:
    """Read JPEG dimensions without an image-processing dependency."""

    if not data.startswith(b"\xff\xd8"):
        raise ValueError("image source is not a JPEG")
    position = 2
    while position + 9 <= len(data):
        if data[position] != 0xFF:
            position += 1
            continue
        marker = data[position + 1]
        position += 2
        if marker in {0xD8, 0xD9}:
            continue
        if position + 2 > len(data):
            break
        length = int.from_bytes(data[position : position + 2], "big")
        if marker in {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }:
            height = int.from_bytes(data[position + 3 : position + 5], "big")
            width = int.from_bytes(data[position + 5 : position + 7], "big")
            return width, height
        if length < 2:
            break
        position += length
    raise ValueError("JPEG does not contain a supported frame header")


def validate_media(record: Mapping[str, Any], body: bytes) -> dict[str, Any]:
    """Apply format-specific full-document admission checks."""

    format_id = record["format_id"]
    requirements = record["format_requirements"]
    if format_id == "jats":
        root = ET.fromstring(body)
        jats_names = [local_name(element.tag) for element in root.iter()]
        dois = {
            "".join(element.itertext()).strip().casefold()
            for element in root.iter()
            if local_name(element.tag) == "article-id"
            and element.attrib.get("pub-id-type") == "doi"
        }
        if (
            local_name(root.tag) != "article"
            or requirements["article_doi"].casefold() not in dois
        ):
            raise ValueError("JATS source identity mismatch")
        if not {"front", "body", "back"} <= set(jats_names):
            raise ValueError("JATS source is not a full article")
        return {
            "root": "article",
            "element_count": len(jats_names),
            "doi": sorted(dois),
        }
    if format_id == "pdf-digital":
        if not body.startswith(b"%PDF-") or b"/Encrypt" in body:
            raise ValueError("PDF is malformed or encrypted")
        pages = len(re.findall(rb"/Type\s*/Page\b", body))
        if pages < requirements["minimum_pages"] or not re.search(rb"BT\s", body):
            raise ValueError("PDF does not prove born-digital multipage text")
        return {"page_objects": pages, "encrypted": False, "text_operators": True}
    if format_id == "html":
        text = body.decode("utf-8")
        parser = ArticleHTML()
        parser.feed(text)
        missing_metadata = [
            name
            for name in requirements["required_metadata"]
            if not parser.metadata.get(name)
        ]
        if missing_metadata:
            raise ValueError(f"HTML article metadata is missing: {missing_metadata}")
        observed_doi = parser.metadata["citation_doi"]
        expected_doi = record["canonical_uri"].removeprefix("https://doi.org/")
        if not any(expected_doi.casefold() in item.casefold() for item in observed_doi):
            raise ValueError("HTML article DOI metadata mismatch")
        has_article_region = parser.article_elements >= 1 or (
            parser.main_elements >= 1 and parser.article_body_regions >= 1
        )
        if not has_article_region or parser.paragraphs < 20 or parser.headings < 5:
            raise ValueError("HTML source lacks substantive article structure")
        return {
            "article_elements": parser.article_elements,
            "article_body_regions": parser.article_body_regions,
            "main_elements": parser.main_elements,
            "headings": parser.headings,
            "paragraphs": parser.paragraphs,
        }
    if format_id == "markdown":
        text = body.decode("utf-8")
        counts = {
            "headings": len(re.findall(r"(?m)^#{1,6} ", text)),
            "lists": len(re.findall(r"(?m)^(?:[-*]|\d+\.) ", text)),
            "table_rows": len(re.findall(r"(?m)^\|.*\|\s*$", text)),
            "fences": len(re.findall(r"(?m)^```", text)),
            "links": len(re.findall(r"\[[^]]+\]\([^)]+\)", text)),
        }
        if not all(counts.values()):
            raise ValueError("Markdown source lacks a required semantic structure")
        return counts
    if format_id == "text":
        text = body.decode("utf-8")
        lines = text.splitlines()
        if (
            len(lines) < requirements["minimum_lines"]
            or "RFC 9110" not in text
            or "HTTP Semantics" not in text
        ):
            raise ValueError("plain-text RFC identity or size mismatch")
        return {"encoding": "utf-8", "lines": len(lines), "characters": len(text)}
    if format_id == "docx":
        with zipfile.ZipFile(BytesIO(body)) as package:
            package_names = set(package.namelist())
            if not set(requirements["required_package_parts"]) <= package_names:
                raise ValueError("DOCX package lacks required OOXML parts")
            if any(
                PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
                for name in package_names
            ):
                raise ValueError("DOCX package contains an unsafe path")
            if sum(info.file_size for info in package.infolist()) > 32 * 1024 * 1024:
                raise ValueError("DOCX expanded content exceeds its safety budget")
            document = ET.fromstring(package.read("word/document.xml"))
        names_by_tag = [local_name(element.tag) for element in document.iter()]
        characters = sum(
            len(element.text or "")
            for element in document.iter()
            if local_name(element.tag) == "t"
        )
        headings = sum(
            1
            for element in document.iter()
            if local_name(element.tag) == "pStyle"
            and (
                element.attrib.get(
                    "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val"
                )
                or ""
            ).startswith("Heading")
        )
        lists = names_by_tag.count("numPr")
        hyperlinks = names_by_tag.count("hyperlink")
        tables = names_by_tag.count("tbl")
        paragraphs = names_by_tag.count("p")
        if (
            characters < 1000
            or not headings
            or not lists
            or not tables
            or not hyperlinks
            or not paragraphs
        ):
            raise ValueError("DOCX source lacks a declared semantic structure")
        return {
            "package_parts": len(package_names),
            "text_characters": characters,
            "headings": headings,
            "paragraphs": paragraphs,
            "lists": lists,
            "tables": tables,
            "hyperlinks": hyperlinks,
        }
    if format_id == "ocr-required":
        width, height = jpeg_dimensions(body)
        if (
            width < requirements["minimum_width_pixels"]
            or height < requirements["minimum_height_pixels"]
        ):
            raise ValueError("OCR specimen dimensions are below policy")
        return {
            "width": width,
            "height": height,
            "required_outcome": "ocr-required",
            "embedded_text": False,
        }
    raise ValueError(f"unsupported parser source format: {format_id}")


def write_exclusive(path: Path, data: bytes) -> None:
    """Create a read-only durable file or accept identical existing bytes."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError(f"refusing to replace different durable bytes: {path}")
        return
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        written = 0
        while written < len(data):
            written += os.write(descriptor, data[written:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def validate_receipt_identity(receipt: Mapping[str, Any]) -> None:
    """Reject incomplete or modified durable acquisition receipts."""

    try:
        recorded_identity = receipt["receipt_identity_sha256"]
        core = {
            key: value
            for key, value in receipt.items()
            if key not in {"retrieved_at", "receipt_identity_sha256"}
        }
    except KeyError as error:
        raise RuntimeError("existing parser source receipt is incomplete") from error
    if recorded_identity != sha256(canonical(core)):
        raise RuntimeError("existing parser source receipt identity mismatch")


def acquire_record(record: Mapping[str, Any], *, output_root: Path) -> dict[str, Any]:
    """Acquire one reviewed source and emit immutable source and receipt records."""

    source_id = record["parser_source_id"]
    extension = EXTENSIONS[record["format_id"]]
    media_path = output_root / "corpus" / f"{source_id}{extension}"
    source_path = output_root / "sources" / f"{source_id}.json"
    receipt_path = output_root / "acquisition-receipts" / f"{source_id}.json"
    source_core = dict(record)
    source_identity = sha256(canonical(source_core))
    source_document = {**source_core, "record_identity_sha256": source_identity}
    source_bytes = canonical(source_document) + b"\n"
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        validate_receipt_identity(receipt)
        body = media_path.read_bytes()
        if (
            receipt["parser_source_id"] != source_id
            or receipt["format_id"] != record["format_id"]
            or receipt["state"] != "acquired"
            or receipt["local_path"] != f"corpus/{source_id}{extension}"
            or receipt["source_record_identity_sha256"] != source_identity
            or receipt["sha256"] != sha256(body)
            or receipt["byte_count"] != len(body)
        ):
            raise RuntimeError(
                f"existing parser source receipt does not match bytes: {source_id}"
            )
        validate_media(record, body)
        write_exclusive(source_path, source_bytes)
        return cast(dict[str, Any], receipt)
    response_body, transport = fetch(record)
    body = apply_transformations(record, response_body)
    inspection = validate_media(record, body)
    license_evidence = fetch_license_evidence(record)
    receipt_core = {
        "schema_version": "bijux.canon.parser_source_acquisition.v1",
        "parser_source_id": source_id,
        "format_id": record["format_id"],
        "source_record_identity_sha256": source_identity,
        "state": "acquired",
        "media_type": transport["content_type"],
        "byte_count": len(body),
        "sha256": sha256(body),
        "local_path": f"corpus/{source_id}{extension}",
        "license": record["license"],
        "license_evidence": license_evidence,
        "attribution": record["attribution"],
        "access_terms": record["access_terms"],
        "redistribution": record["redistribution"],
        "transformations": record["transformations"],
        "inspection": inspection,
        "transport": transport,
    }
    receipt = {
        **receipt_core,
        "retrieved_at": utc_now(),
        "receipt_identity_sha256": sha256(canonical(receipt_core)),
    }
    write_exclusive(media_path, body)
    write_exclusive(source_path, source_bytes)
    write_exclusive(receipt_path, canonical(receipt) + b"\n")
    return receipt


def main() -> None:
    """Acquire the declared parser portfolio."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--portfolio", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    records = load_portfolio(args.portfolio.resolve(strict=True))
    receipts = [
        acquire_record(record, output_root=args.output_root) for record in records
    ]
    result = {
        "schema_version": "bijux.canon.parser_source_acquisition_run.v1",
        "source_count": len(receipts),
        "total_bytes": sum(receipt["byte_count"] for receipt in receipts),
        "sources": [
            {
                "parser_source_id": receipt["parser_source_id"],
                "format_id": receipt["format_id"],
                "sha256": receipt["sha256"],
                "byte_count": receipt["byte_count"],
                "receipt_identity_sha256": receipt["receipt_identity_sha256"],
            }
            for receipt in receipts
        ],
    }
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
