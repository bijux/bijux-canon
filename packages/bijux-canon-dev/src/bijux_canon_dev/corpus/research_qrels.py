#!/usr/bin/env python3
"""Validate source-first graded qrels against immutable ingest chunks."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping, TypeGuard

from bijux_canon_dev.corpus.acquisition import canonical, sha256
from bijux_canon_dev.corpus.research_corpus_lock import (
    read_object,
    validate_lock_document,
)
from bijux_canon_dev.corpus.research_locator_truth import (
    load_truth as load_locator_truth,
    validate_truth as validate_locator_truth,
)


SCHEMA_VERSION = "bijux.canon.research_qrel.v1"
CHUNK_SCHEMA_VERSION = "bijux.canon.ingest.semantic_chunk.v1"
ADJUDICATOR_ID = "bijux-corpus-curation-primary"
ADJUDICATION_STATUS = "primary_review_complete"
LABEL_ORIGIN = "manual-source-first-no-system-ranking"
REVIEW_METHOD = "manual source-first adjudication before retrieval evaluation"
TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def identity(value: object) -> str:
    """Return an ingest-compatible canonical SHA-256 identity."""

    return f"sha256:{sha256(canonical(value))}"


def is_identity(value: object) -> TypeGuard[str]:
    """Return whether a value is a lowercase prefixed SHA-256 identity."""

    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def qrel_identity(record: Mapping[str, Any]) -> str:
    """Return the canonical identity of one qrel record."""

    core = {
        key: value for key, value in record.items() if key != "qrel_identity_sha256"
    }
    return sha256(canonical(core))


def load_qrels(path: Path) -> list[dict[str, Any]]:
    """Load canonical qrels from a regular, non-symlink JSONL file."""

    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"research qrels are not a regular file: {path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_bytes().splitlines(), 1):
        if not line:
            raise RuntimeError(f"blank research qrel line: {line_number}")
        value = json.loads(line)
        if not isinstance(value, dict) or canonical(value) != line:
            raise RuntimeError(f"non-canonical research qrel line: {line_number}")
        records.append(value)
    return records


def _validate_chunk(
    chunk: Mapping[str, Any],
    *,
    source_sha256: str,
    anchor_texts: list[str],
) -> str:
    if chunk.get("schema_version") != CHUNK_SCHEMA_VERSION:
        raise RuntimeError("research qrel chunk schema mismatch")
    if chunk.get("source_content_sha256") != source_sha256:
        raise RuntimeError("research qrel chunk source mismatch")
    mapping_ids = chunk.get("mapping_sha256")
    text = chunk.get("normalized_text")
    block_roles = chunk.get("block_roles")
    section_paths = chunk.get("section_paths")
    policy_id = chunk.get("chunking_policy_sha256")
    if (
        not isinstance(mapping_ids, list)
        or not mapping_ids
        or any(not is_identity(mapping_id) for mapping_id in mapping_ids)
        or not is_identity(policy_id)
        or not isinstance(text, str)
        or not text
        or not isinstance(block_roles, list)
        or any(not isinstance(role, str) or not role for role in block_roles)
        or not isinstance(section_paths, list)
        or any(
            not isinstance(path, list)
            or any(not isinstance(part, str) or not part for part in path)
            for path in section_paths
        )
        or len(block_roles) != len(mapping_ids)
        or len(section_paths) != len(mapping_ids)
    ):
        raise RuntimeError("research qrel chunk manifest mismatch")
    if any(anchor not in text for anchor in anchor_texts):
        raise RuntimeError("research qrel anchor is absent from its chunk")
    fingerprint = identity(
        {
            "block_roles": block_roles,
            "normalized_text_sha256": sha256(text.encode()),
            "section_paths": section_paths,
        }
    )
    chunk_id = identity(
        {
            "canonical_fingerprint": fingerprint,
            "chunking_policy_sha256": policy_id,
            "mapping_sha256": mapping_ids,
            "source_content_sha256": source_sha256,
        }
    )
    required = {
        "canonical_fingerprint": fingerprint,
        "character_count": len(text),
        "chunk_id": chunk_id,
        "mapping_sha256": mapping_ids,
        "normalized_text_sha256": sha256(text.encode()),
        "token_count": len(TOKEN.findall(text)),
    }
    drift = [key for key, expected in required.items() if chunk.get(key) != expected]
    if drift:
        raise RuntimeError(f"research qrel chunk identity drift: {drift}")
    chunk_index = chunk.get("chunk_index")
    overlap = chunk.get("overlap_character_count")
    if (
        not isinstance(chunk_index, int)
        or isinstance(chunk_index, bool)
        or chunk_index < 0
        or not isinstance(overlap, int)
        or isinstance(overlap, bool)
        or not 0 <= overlap < len(text)
    ):
        raise RuntimeError("research qrel chunk bounds are invalid")
    return chunk_id


def validate_qrels(
    records: list[dict[str, Any]],
    *,
    lock_path: Path,
    locator_truth_path: Path,
    research_root: Path,
) -> dict[str, Any]:
    """Validate graded qrels, complete anchors, and canonical chunk lineage."""

    research_root = research_root.resolve(strict=True)
    lock = read_object(lock_path.resolve(strict=True))
    validate_lock_document(lock, research_root=research_root)
    locator_records = load_locator_truth(locator_truth_path.resolve(strict=True))
    validate_locator_truth(
        locator_records,
        lock_path=lock_path,
        research_root=research_root,
    )
    sources = {source["source_id"]: source for source in lock["sources"]}
    locators = {record["truth_id"]: record for record in locator_records}
    observed_anchors: Counter[str] = Counter()
    qrel_ids: set[str] = set()
    query_chunks: set[tuple[str, str]] = set()
    query_by_source: dict[str, tuple[str, str]] = {}
    grades_by_source: dict[str, set[int]] = {source_id: set() for source_id in sources}
    snapshot_ids: set[str] = set()

    for record in records:
        source_id = record.get("source_id")
        if not isinstance(source_id, str) or source_id not in sources:
            raise RuntimeError(f"unknown research qrel source: {source_id}")
        source = sources[source_id]
        required = {
            "schema_version": SCHEMA_VERSION,
            "source_sha256": source["sha256"],
            "lock_identity_sha256": lock["lock_identity_sha256"],
            "adjudicator_id": ADJUDICATOR_ID,
            "adjudication_status": ADJUDICATION_STATUS,
            "label_origin": LABEL_ORIGIN,
            "review_method": REVIEW_METHOD,
            "system_ranking_consulted": False,
        }
        drift = [
            key for key, expected in required.items() if record.get(key) != expected
        ]
        if drift:
            raise RuntimeError(f"research qrel metadata drift for {source_id}: {drift}")
        qrel_id = record.get("qrel_id")
        query_id = record.get("query_id")
        query = record.get("query")
        rationale = record.get("rationale")
        grade = record.get("relevance_grade")
        if (
            not isinstance(qrel_id, str)
            or not qrel_id.startswith(f"{source_id}::qrel::")
            or qrel_id in qrel_ids
            or query_id != f"{source_id}::research-question"
            or not isinstance(query, str)
            or len(query) < 24
            or not isinstance(rationale, str)
            or len(rationale) < 40
            or not isinstance(grade, int)
            or isinstance(grade, bool)
            or grade not in {1, 2, 3}
        ):
            raise RuntimeError(f"invalid research qrel judgment: {qrel_id}")
        qrel_ids.add(qrel_id)
        grades_by_source[source_id].add(grade)
        query_pair = (str(query_id), query)
        previous_query = query_by_source.setdefault(source_id, query_pair)
        if previous_query != query_pair:
            raise RuntimeError(f"research qrel query drift for {source_id}")
        try:
            date.fromisoformat(record["reviewed_on"])
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError(
                f"invalid research qrel review date: {qrel_id}"
            ) from error
        snapshot_id = record.get("ingest_snapshot_id")
        if not is_identity(snapshot_id):
            raise RuntimeError(f"invalid research qrel snapshot identity: {qrel_id}")
        snapshot_ids.add(snapshot_id)
        anchor_ids = record.get("anchor_truth_ids")
        if (
            not isinstance(anchor_ids, list)
            or not anchor_ids
            or anchor_ids != sorted(set(anchor_ids))
        ):
            raise RuntimeError(f"invalid research qrel anchors: {qrel_id}")
        anchor_records: list[dict[str, Any]] = []
        for anchor_id in anchor_ids:
            anchor = locators.get(anchor_id)
            if anchor is None or anchor["source_id"] != source_id:
                raise RuntimeError(f"unknown research qrel anchor: {anchor_id}")
            observed_anchors[anchor_id] += 1
            anchor_records.append(anchor)
        chunk = record.get("chunk")
        if not isinstance(chunk, dict):
            raise RuntimeError(f"research qrel chunk is not an object: {qrel_id}")
        chunk_id = _validate_chunk(
            chunk,
            source_sha256=source["sha256"],
            anchor_texts=[anchor["exact_text"] for anchor in anchor_records],
        )
        query_chunk = (str(query_id), chunk_id)
        if query_chunk in query_chunks:
            raise RuntimeError(f"duplicate research query-chunk judgment: {qrel_id}")
        query_chunks.add(query_chunk)
        if record.get("qrel_identity_sha256") != qrel_identity(record):
            raise RuntimeError(f"research qrel identity mismatch: {qrel_id}")

    if set(query_by_source) != set(sources):
        raise RuntimeError("research qrel source coverage mismatch")
    if any(grades != {1, 2, 3} for grades in grades_by_source.values()):
        raise RuntimeError("research qrel grade coverage mismatch")
    if observed_anchors != Counter({truth_id: 1 for truth_id in locators}):
        raise RuntimeError("research qrel locator-anchor coverage mismatch")
    if len(snapshot_ids) != 1:
        raise RuntimeError("research qrels do not share one ingest snapshot")
    return {
        "anchor_count": len(observed_anchors),
        "ingest_snapshot_id": next(iter(snapshot_ids)),
        "qrel_count": len(records),
        "qrel_set_sha256": sha256(
            b"".join(canonical(record) + b"\n" for record in records)
        ),
        "source_count": len(sources),
    }


def main() -> None:
    """Validate the durable research qrels."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--locator-truth", type=Path, required=True)
    parser.add_argument("--qrels", type=Path, required=True)
    parser.add_argument("--research-root", type=Path, required=True)
    args = parser.parse_args()
    result = validate_qrels(
        load_qrels(args.qrels),
        lock_path=args.lock,
        locator_truth_path=args.locator_truth,
        research_root=args.research_root,
    )
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
