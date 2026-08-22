#!/usr/bin/env python3
"""Validate independently reviewed exact locators in a research corpus."""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping
from datetime import date
import json
from pathlib import Path
import re
import sys
from typing import Any
import xml.etree.ElementTree as ET

from bijux_canon_dev.corpus.acquisition import canonical, sha256
from bijux_canon_dev.corpus.research_corpus_lock import (
    read_object,
    validate_lock_document,
)

SCHEMA_VERSION = "bijux.canon.research_locator_truth.v1"
REVIEW_METHOD = "independent manual inspection of immutable source bytes"
NORMALIZATION = "collapse-unicode-whitespace-v1"
REQUIRED_ROLES = {
    "article-title",
    "abstract-paragraph",
    "body-section-heading",
    "body-paragraph",
}
PATH_PART = re.compile(r"^(?P<tag>[A-Za-z0-9_-]+)(?:\[(?P<index>[1-9][0-9]*)\])?$")


def collapse_whitespace(parts: Iterable[str]) -> str:
    """Collapse source-rendering whitespace without changing text order."""

    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def local_name(tag: str) -> str:
    """Return an XML element's namespace-free local name."""

    return tag.rsplit("}", 1)[-1]


def truth_identity(record: Mapping[str, Any]) -> str:
    """Return the canonical identity of one truth record."""

    core = {
        key: value for key, value in record.items() if key != "truth_identity_sha256"
    }
    return sha256(canonical(core))


def load_truth(path: Path) -> list[dict[str, Any]]:
    """Load canonical JSONL truth from a regular, non-symlink file."""

    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"research locator truth is not a regular file: {path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_bytes().splitlines(), 1):
        if not line:
            raise RuntimeError(f"blank research locator truth line: {line_number}")
        value = json.loads(line)
        if not isinstance(value, dict) or canonical(value) != line:
            raise RuntimeError(
                f"non-canonical research locator truth line: {line_number}"
            )
        records.append(value)
    return records


def resolve_element_path(root: ET.Element, path: str) -> ET.Element:
    """Resolve a namespace-independent, one-based JATS element path."""

    if not isinstance(path, str) or not path.startswith("/"):
        raise RuntimeError(f"JATS locator path is not absolute: {path}")
    parts: list[tuple[str, int]] = []
    for part in path.removeprefix("/").split("/"):
        match = PATH_PART.fullmatch(part)
        if match is None:
            raise RuntimeError(f"invalid JATS locator component: {part}")
        parts.append((match.group("tag"), int(match.group("index") or "1")))
    root_name, root_index = parts.pop(0)
    if root_name != local_name(root.tag) or root_index != 1:
        raise RuntimeError(f"JATS locator root mismatch: {path}")
    node = root
    for name, index in parts:
        matches = [child for child in node if local_name(child.tag) == name]
        if index > len(matches):
            raise RuntimeError(f"JATS locator does not resolve: {path}")
        node = matches[index - 1]
    return node


def _validate_record_metadata(
    record: Mapping[str, Any],
    *,
    source: Mapping[str, Any],
    lock_identity_sha256: str,
) -> tuple[str, str]:
    source_id = source["source_id"]
    role = record.get("block_role")
    required = {
        "schema_version": SCHEMA_VERSION,
        "source_id": source_id,
        "format_id": "jats",
        "source_sha256": source["sha256"],
        "lock_identity_sha256": lock_identity_sha256,
        "disposition": "verified_complete",
        "locator_scheme": "jats-element-path-and-character-span",
        "exact_text_normalization": NORMALIZATION,
        "review_method": REVIEW_METHOD,
    }
    drift = [key for key, expected in required.items() if record.get(key) != expected]
    if drift:
        raise RuntimeError(f"research locator metadata drift for {source_id}: {drift}")
    if role not in REQUIRED_ROLES:
        raise RuntimeError(f"invalid research locator role for {source_id}: {role}")
    truth_id = record.get("truth_id")
    if truth_id != f"{source_id}::{role}":
        raise RuntimeError(f"research locator truth ID drift: {truth_id}")
    try:
        date.fromisoformat(record["reviewed_on"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError(
            f"research locator review date is invalid: {truth_id}"
        ) from error
    if record.get("truth_identity_sha256") != truth_identity(record):
        raise RuntimeError(f"research locator truth identity mismatch: {truth_id}")
    return str(truth_id), str(role)


def validate_truth(
    records: list[dict[str, Any]],
    *,
    lock_path: Path,
    research_root: Path,
) -> dict[str, Any]:
    """Validate complete role coverage and exact text resolution for every source."""

    research_root = research_root.resolve(strict=True)
    lock = read_object(lock_path.resolve(strict=True))
    validate_lock_document(lock, research_root=research_root)
    sources = {source["source_id"]: source for source in lock["sources"]}
    roles: dict[str, set[str]] = {source_id: set() for source_id in sources}
    truth_ids: set[str] = set()
    truth_identities: set[str] = set()
    xml_roots: dict[str, ET.Element] = {}

    for record in records:
        source_id_value = record.get("source_id")
        if not isinstance(source_id_value, str) or source_id_value not in sources:
            raise RuntimeError(f"unknown research locator source: {source_id_value}")
        source_id = source_id_value
        source = sources[source_id]
        truth_id, role = _validate_record_metadata(
            record,
            source=source,
            lock_identity_sha256=lock["lock_identity_sha256"],
        )
        identity = record["truth_identity_sha256"]
        if (
            truth_id in truth_ids
            or identity in truth_identities
            or role in roles[source_id]
        ):
            raise RuntimeError(f"duplicate research locator truth: {truth_id}")
        truth_ids.add(truth_id)
        truth_identities.add(identity)
        roles[source_id].add(role)

        root = xml_roots.get(source_id)
        if root is None:
            root = ET.fromstring((research_root / source["local_path"]).read_bytes())
            xml_roots[source_id] = root
        locator = record.get("locator")
        if not isinstance(locator, dict):
            raise RuntimeError(f"research locator is not an object: {truth_id}")
        element_path = locator.get("element_path")
        if not isinstance(element_path, str):
            raise RuntimeError(f"research element path is not a string: {truth_id}")
        node = resolve_element_path(root, element_path)
        normalized = collapse_whitespace(node.itertext())
        start = locator.get("character_start")
        end = locator.get("character_end")
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or start < 0
            or end <= start
            or end > len(normalized)
        ):
            raise RuntimeError(f"invalid research character span: {truth_id}")
        exact_text = record.get("exact_text")
        if (
            not isinstance(exact_text, str)
            or not exact_text
            or normalized[start:end] != exact_text
            or record.get("exact_text_sha256") != sha256(exact_text.encode())
        ):
            raise RuntimeError(f"research locator exact text mismatch: {truth_id}")

    for source_id, observed_roles in roles.items():
        if observed_roles != REQUIRED_ROLES:
            raise RuntimeError(
                f"research locator role coverage mismatch for {source_id}: "
                f"{sorted(observed_roles)}"
            )
    return {
        "lock_identity_sha256": lock["lock_identity_sha256"],
        "record_count": len(records),
        "source_count": len(sources),
        "truth_set_sha256": sha256(
            b"".join(canonical(record) + b"\n" for record in records)
        ),
    }


def main() -> None:
    """Validate the durable research locator-truth set."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--truth", type=Path, required=True)
    args = parser.parse_args()
    result = validate_truth(
        load_truth(args.truth),
        lock_path=args.lock,
        research_root=args.research_root,
    )
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
