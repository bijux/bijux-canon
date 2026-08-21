#!/usr/bin/env python3
"""Validate independently authored locator truth for locked parser sources."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from bijux_canon_dev.corpus.parser_lock import (
    read_json,
    validate_lock_document,
)
from bijux_canon_dev.corpus.parser_sources import canonical, load_portfolio, sha256


SCHEMA_VERSION = "bijux.canon.parser_locator_truth.v1"
REVIEW_METHOD = "independent manual inspection of immutable source bytes"
VOID_HTML_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
OOXML_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
PATH_PART = re.compile(r"^(?P<tag>[A-Za-z0-9_-]+)(?:\[(?P<index>[1-9][0-9]*)\])?$")


def collapse_whitespace(parts: Iterable[str]) -> str:
    """Collapse source-rendering whitespace without changing characters."""

    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def truth_identity(record: Mapping[str, Any]) -> str:
    """Return the canonical identity of one truth record."""

    core = {
        key: value for key, value in record.items() if key != "truth_identity_sha256"
    }
    return sha256(canonical(core))


def load_truth(path: Path) -> list[dict[str, Any]]:
    """Load canonical JSONL truth from a regular, non-symlink file."""

    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"locator truth is not a regular file: {path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_bytes().splitlines(), 1):
        if not line.strip():
            raise RuntimeError(f"blank locator truth line: {line_number}")
        value = json.loads(line)
        if not isinstance(value, dict) or canonical(value) != line:
            raise RuntimeError(f"non-canonical locator truth line: {line_number}")
        records.append(value)
    return records


def local_name(tag: str) -> str:
    """Return an XML element's namespace-free local name."""

    return tag.rsplit("}", 1)[-1]


def indexed_path_parts(path: str) -> list[tuple[str, int]]:
    """Parse a one-based element path."""

    if not path.startswith("/"):
        raise RuntimeError(f"locator path is not absolute: {path}")
    result: list[tuple[str, int]] = []
    for part in path.removeprefix("/").split("/"):
        match = PATH_PART.fullmatch(part)
        if match is None:
            raise RuntimeError(f"invalid locator path component: {part}")
        result.append((match.group("tag"), int(match.group("index") or "1")))
    return result


def resolve_xml_path(root: ET.Element, path: str) -> ET.Element:
    """Resolve a namespace-independent, one-based XML element path."""

    parts = indexed_path_parts(path)
    root_name, root_index = parts.pop(0)
    if root_name != local_name(root.tag) or root_index != 1:
        raise RuntimeError(f"XML locator root mismatch: {path}")
    node = root
    for name, index in parts:
        matches = [child for child in node if local_name(child.tag) == name]
        if index > len(matches):
            raise RuntimeError(f"XML locator does not resolve: {path}")
        node = matches[index - 1]
    return node


@dataclass(eq=False)
class HTMLElement:
    """Minimal ordered HTML node used for deterministic DOM truth checks."""

    tag: str
    parent: HTMLElement | None
    contents: list[str | HTMLElement] = field(default_factory=list)


class HTMLTree(HTMLParser):
    """Build a minimal source-order tree from the reviewed HTML document."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root: HTMLElement | None = None
        self.stack: list[HTMLElement] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        node = HTMLElement(tag=tag, parent=self.stack[-1] if self.stack else None)
        if node.parent is None:
            if self.root is not None:
                raise RuntimeError("HTML locator source has multiple roots")
            self.root = node
        else:
            node.parent.contents.append(node)
        if tag not in VOID_HTML_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if self.stack and self.stack[-1].tag == tag:
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if self.stack:
            self.stack[-1].contents.append(data)


def html_children(node: HTMLElement) -> list[HTMLElement]:
    """Return only element children from an ordered HTML node."""

    return [item for item in node.contents if isinstance(item, HTMLElement)]


def resolve_html_path(root: HTMLElement, path: str) -> HTMLElement:
    """Resolve a one-based HTML DOM path."""

    parts = indexed_path_parts(path)
    root_name, root_index = parts.pop(0)
    if root_name != root.tag or root_index != 1:
        raise RuntimeError(f"HTML locator root mismatch: {path}")
    node = root
    for name, index in parts:
        matches = [child for child in html_children(node) if child.tag == name]
        if index > len(matches):
            raise RuntimeError(f"HTML locator does not resolve: {path}")
        node = matches[index - 1]
    return node


def html_text(node: HTMLElement) -> str:
    """Return source-ordered descendant text with declared whitespace collapse."""

    def parts(current: HTMLElement) -> Iterable[str]:
        for item in current.contents:
            if isinstance(item, str):
                yield item
            else:
                yield from parts(item)

    return collapse_whitespace(parts(node))


def verify_line_locator(record: Mapping[str, Any], media_path: Path) -> str:
    """Resolve an exact Markdown or plain-text line span."""

    encoding = "utf-8-sig" if record["format_id"] == "text" else "utf-8"
    lines = media_path.read_text(encoding=encoding).splitlines()
    locator = record["locator"]
    start = locator.get("line_start")
    end = locator.get("line_end")
    if (
        not isinstance(start, int)
        or not isinstance(end, int)
        or start < 1
        or end < start
        or end > len(lines)
    ):
        raise RuntimeError(f"invalid line locator: {record['truth_id']}")
    return "\n".join(lines[start - 1 : end])


def verify_docx_locator(record: Mapping[str, Any], media_path: Path) -> str:
    """Resolve an OOXML package-part and block locator."""

    locator = record["locator"]
    if locator.get("package_part") != "word/document.xml":
        raise RuntimeError(f"unsupported DOCX package part: {record['truth_id']}")
    with ZipFile(media_path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    body = root.find("w:body", OOXML_NAMESPACE)
    if body is None:
        raise RuntimeError("DOCX document body is absent")
    block_index = locator.get("block_index")
    if not isinstance(block_index, int) or not 1 <= block_index <= len(body):
        raise RuntimeError(f"invalid DOCX block locator: {record['truth_id']}")
    node = list(body)[block_index - 1]
    if local_name(node.tag) != locator.get("block_kind"):
        raise RuntimeError(f"DOCX block kind drift: {record['truth_id']}")
    table_cell_index = locator.get("table_cell_index")
    hyperlink_index = locator.get("hyperlink_index")
    if table_cell_index is not None:
        cells = node.findall(".//w:tc", OOXML_NAMESPACE)
        if not isinstance(table_cell_index, int) or not 1 <= table_cell_index <= len(
            cells
        ):
            raise RuntimeError(f"invalid DOCX table cell: {record['truth_id']}")
        node = cells[table_cell_index - 1]
    if hyperlink_index is not None:
        hyperlinks = node.findall(".//w:hyperlink", OOXML_NAMESPACE)
        if not isinstance(hyperlink_index, int) or not 1 <= hyperlink_index <= len(
            hyperlinks
        ):
            raise RuntimeError(f"invalid DOCX hyperlink: {record['truth_id']}")
        node = hyperlinks[hyperlink_index - 1]
    return collapse_whitespace(
        text.text or "" for text in node.findall(".//w:t", OOXML_NAMESPACE)
    )


def verify_pdf_locator(record: Mapping[str, Any], page_count: int) -> None:
    """Validate a manually reviewed PDF page-text-span locator."""

    locator = record["locator"]
    page = locator.get("page_number")
    start = locator.get("text_start")
    end = locator.get("text_end")
    exact_text = record["exact_text"]
    if (
        locator.get("extractor") != "pypdf-6.14.2-page-extract-text"
        or not isinstance(page, int)
        or not 1 <= page <= page_count
        or not isinstance(start, int)
        or not isinstance(end, int)
        or start < 0
        or end <= start
        or end - start != len(exact_text)
        or not re.fullmatch(r"[0-9a-f]{64}", locator.get("page_text_sha256", ""))
    ):
        raise RuntimeError(f"invalid PDF locator: {record['truth_id']}")


def validate_truth(
    records: list[dict[str, Any]],
    *,
    portfolio_path: Path,
    output_root: Path,
    lock_path: Path,
) -> dict[str, Any]:
    """Validate truth identities, required coverage, and resolvable source locators."""

    output_root = output_root.resolve(strict=True)
    portfolio = load_portfolio(portfolio_path.resolve(strict=True))
    source_records = {record["parser_source_id"]: record for record in portfolio}
    lock = read_json(lock_path.resolve(strict=True))
    validate_lock_document(lock)
    locked_sources = {source["parser_source_id"]: source for source in lock["sources"]}
    if set(source_records) != set(locked_sources):
        raise RuntimeError("locator truth portfolio and lock identities differ")

    identities: set[str] = set()
    truth_ids: set[str] = set()
    roles: dict[str, set[str]] = {source_id: set() for source_id in source_records}
    xml_cache: dict[str, ET.Element] = {}
    html_cache: dict[str, HTMLTree] = {}
    for record in records:
        source_id_value = record.get("parser_source_id")
        if (
            not isinstance(source_id_value, str)
            or source_id_value not in source_records
        ):
            raise RuntimeError(f"unknown locator truth source: {source_id_value}")
        source_id = source_id_value
        source = source_records[source_id]
        locked = locked_sources[source_id]
        normalization = {
            "jats": "collapse-unicode-whitespace-v1",
            "pdf-digital": "pypdf-6.14.2-page-extract-text",
            "html": "collapse-unicode-whitespace-v1",
            "markdown": "source-lines-with-lf-join-v1",
            "text": "source-lines-with-lf-join-v1",
            "docx": "collapse-unicode-whitespace-v1",
            "ocr-required": None,
        }[source["format_id"]]
        required = {
            "schema_version": SCHEMA_VERSION,
            "format_id": source["format_id"],
            "source_record_uri": f"sources/{source_id}.json",
            "media_path": locked["local_path"],
            "source_sha256": locked["sha256"],
            "lock_identity_sha256": lock["lock_identity_sha256"],
            "disposition": source["expected_disposition"],
            "locator_scheme": source["truth_requirements"]["locator_scheme"],
            "exact_text_normalization": normalization,
            "review_method": REVIEW_METHOD,
        }
        drift = [
            key for key, expected in required.items() if record.get(key) != expected
        ]
        if drift:
            raise RuntimeError(f"locator truth metadata drift for {source_id}: {drift}")
        truth_id_value = record.get("truth_id")
        if not isinstance(truth_id_value, str) or truth_id_value in truth_ids:
            raise RuntimeError(
                f"duplicate or invalid locator truth ID: {truth_id_value}"
            )
        truth_ids.add(truth_id_value)
        try:
            date.fromisoformat(record["reviewed_on"])
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError(
                f"locator truth review date is invalid: {truth_id_value}"
            ) from error
        identity = record.get("truth_identity_sha256")
        if identity != truth_identity(record) or identity in identities:
            raise RuntimeError(f"locator truth identity mismatch: {truth_id_value}")
        identities.add(identity)
        media_path = output_root / locked["local_path"]
        if (
            media_path.is_symlink()
            or sha256(media_path.read_bytes()) != locked["sha256"]
        ):
            raise RuntimeError(f"locator truth media drift: {source_id}")

        role = record.get("block_role")
        if not isinstance(role, str) or role in roles[source_id]:
            raise RuntimeError(
                f"duplicate or invalid locator role for {source_id}: {role}"
            )
        if truth_id_value != f"{source_id}::{role}":
            raise RuntimeError(f"locator truth ID drift: {truth_id_value}")
        roles[source_id].add(role)
        if source["format_id"] == "ocr-required":
            if (
                role != "ocr-required-outcome"
                or record.get("expected_outcome") != "ocr-required"
                or record.get("exact_text") is not None
                or record.get("exact_text_sha256") is not None
                or record.get("locator")
                != {
                    "height": locked["inspection"]["height"],
                    "unit": "pixel",
                    "width": locked["inspection"]["width"],
                    "x": 0,
                    "y": 0,
                }
            ):
                raise RuntimeError(
                    "OCR-required truth is not the typed full-image outcome"
                )
            continue

        exact_text = record.get("exact_text")
        if (
            not isinstance(exact_text, str)
            or not exact_text
            or record.get("exact_text_sha256") != sha256(exact_text.encode())
        ):
            raise RuntimeError(f"locator exact-text hash mismatch: {truth_id_value}")
        format_id = source["format_id"]
        resolved: str | None = None
        if format_id == "jats":
            root = xml_cache.setdefault(
                source_id, ET.fromstring(media_path.read_bytes())
            )
            xml_node = resolve_xml_path(root, record["locator"]["element_path"])
            resolved = collapse_whitespace(xml_node.itertext())
        elif format_id == "html":
            tree = html_cache.get(source_id)
            if tree is None:
                tree = HTMLTree()
                tree.feed(media_path.read_text(encoding="utf-8"))
                if tree.root is None:
                    raise RuntimeError("HTML locator source has no document root")
                html_cache[source_id] = tree
            if tree.root is None:
                raise RuntimeError("HTML locator source has no document root")
            html_node = resolve_html_path(tree.root, record["locator"]["dom_path"])
            resolved = html_text(html_node)
        elif format_id in {"markdown", "text"}:
            resolved = verify_line_locator(record, media_path)
        elif format_id == "docx":
            resolved = verify_docx_locator(record, media_path)
        elif format_id == "pdf-digital":
            verify_pdf_locator(record, locked["inspection"]["page_objects"])
        else:
            raise RuntimeError(f"unsupported locator truth format: {format_id}")
        if resolved is not None and resolved != exact_text:
            raise RuntimeError(f"locator does not resolve exact text: {truth_id_value}")

    for source_id, source in source_records.items():
        requirements = source["truth_requirements"]
        expected_roles = set(requirements.get("representative_blocks", []))
        if requirements.get("required_outcome") == "ocr-required":
            expected_roles = {"ocr-required-outcome"}
        if roles[source_id] != expected_roles:
            raise RuntimeError(
                f"locator truth role coverage mismatch for {source_id}: "
                f"{sorted(roles[source_id])}"
            )
    return {
        "lock_identity_sha256": lock["lock_identity_sha256"],
        "record_count": len(records),
        "source_count": len(source_records),
        "truth_set_sha256": sha256(
            b"".join(canonical(record) + b"\n" for record in records)
        ),
    }


def main() -> None:
    """Validate the durable parser locator-truth set."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--portfolio", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--truth", type=Path, required=True)
    args = parser.parse_args()
    result = validate_truth(
        load_truth(args.truth),
        portfolio_path=args.portfolio,
        output_root=args.output_root,
        lock_path=args.lock,
    )
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
