# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from bijux_canon_ingest import (
    CorpusSnapshotConfiguration,
    CorpusSnapshotDocument,
    DiscoveredSource,
    SemanticChunkingPolicy,
    SourceMetadataRecord,
    admit_source,
    apply_corpus_delta,
    build_corpus_snapshot,
    build_document_span_mappings,
    chunk_document_mappings,
    normalize_source_metadata,
    parse_text,
    plan_corpus_delta,
)

POLICY = SemanticChunkingPolicy(max_characters=80, overlap_characters=12)
CONFIGURATION = CorpusSnapshotConfiguration(
    corpus_name="incremental-research",
    chunking_policy=POLICY,
)


def _document(
    path: Path,
    root: Path,
    *,
    title: str = "Incremental corpus document",
) -> CorpusSnapshotDocument:
    content = path.read_bytes()
    source = DiscoveredSource.create(
        root_name="research",
        relative_path=path.relative_to(root).as_posix(),
        filesystem_path=path,
        content_sha256=hashlib.sha256(content).hexdigest(),
        byte_length=len(content),
        media_type="text/plain",
        is_symlink=False,
    )
    admission = admit_source(source)
    assert admission.admitted and admission.format_id == "text"
    parsed = parse_text(admission)
    metadata = normalize_source_metadata(
        source,
        format_id="text",
        records=(
            SourceMetadataRecord(
                provenance="research-catalog",
                title=title,
                authors=("Researcher",),
                publication_date="2026-08-21",
                language="en",
                license_expression="CC-BY-4.0",
            ),
        ),
    )
    mappings = build_document_span_mappings(content, parsed)
    chunks = chunk_document_mappings(parsed, mappings, policy=POLICY)
    return CorpusSnapshotDocument(admission, parsed, metadata, mappings, chunks)


def _write(path: Path, marker: str) -> None:
    path.write_text(
        f"{marker}\n\n" + (f"Evidence for {marker}. " * 20),
        encoding="utf-8",
    )


def _transition(
    root: Path,
) -> tuple[
    tuple[CorpusSnapshotDocument, ...],
    tuple[CorpusSnapshotDocument, ...],
]:
    root.mkdir()
    stable = root / "stable.txt"
    modified = root / "modified.txt"
    deleted = root / "deleted.txt"
    renamed_before = root / "renamed-before.txt"
    for path, marker in (
        (stable, "stable"),
        (modified, "old modified"),
        (deleted, "deleted"),
        (renamed_before, "renamed"),
    ):
        _write(path, marker)
    previous = tuple(
        _document(path, root) for path in (stable, modified, deleted, renamed_before)
    )

    modified.unlink()
    _write(modified, "new modified")
    deleted.unlink()
    renamed_after = root / "renamed-after.txt"
    renamed_before.rename(renamed_after)
    added = root / "added.txt"
    _write(added, "added")
    current = tuple(
        _document(path, root) for path in (stable, modified, renamed_after, added)
    )
    return previous, current


def test_delta_classifies_add_modify_delete_rename_and_tombstones(
    tmp_path: Path,
) -> None:
    previous_documents, current_documents = _transition(tmp_path / "documents")
    previous = build_corpus_snapshot(CONFIGURATION, previous_documents)
    current = build_corpus_snapshot(CONFIGURATION, current_documents)

    delta = plan_corpus_delta(previous, current)

    assert len(delta.added_document_ids) == 1
    assert len(delta.deleted_document_ids) == 1
    assert len(delta.modifications) == 1
    assert len(delta.renames) == 1
    assert {item.reason for item in delta.tombstones} == {"deleted", "modified"}
    assert delta.added_chunk_ids
    assert delta.invalidated_chunk_ids
    assert not set(delta.added_chunk_ids) & set(delta.invalidated_chunk_ids)
    assert delta.renames[0].previous_relative_path == "renamed-before.txt"
    assert delta.renames[0].current_relative_path == "renamed-after.txt"
    assert delta.manifest() == plan_corpus_delta(previous, current).manifest()


def test_incremental_application_matches_clean_rebuild(
    tmp_path: Path,
) -> None:
    previous_documents, current_documents = _transition(tmp_path / "documents")
    previous = build_corpus_snapshot(CONFIGURATION, previous_documents)
    clean_rebuild = build_corpus_snapshot(CONFIGURATION, current_documents)
    delta = plan_corpus_delta(previous, clean_rebuild)

    incrementally_applied = apply_corpus_delta(
        previous,
        delta,
        CONFIGURATION,
        reversed(current_documents),
    )

    assert incrementally_applied.snapshot_id == clean_rebuild.snapshot_id
    assert incrementally_applied.canonical_bytes == clean_rebuild.canonical_bytes


def test_delta_invalidates_metadata_only_modification(tmp_path: Path) -> None:
    root = tmp_path / "documents"
    root.mkdir()
    source_path = root / "metadata.txt"
    _write(source_path, "metadata")
    before = _document(source_path, root, title="Original title")
    after = _document(source_path, root, title="Corrected title")

    delta = plan_corpus_delta(
        build_corpus_snapshot(CONFIGURATION, (before,)),
        build_corpus_snapshot(CONFIGURATION, (after,)),
    )

    assert len(delta.modifications) == 1
    assert delta.modifications[0].previous_content_sha256 == (
        delta.modifications[0].current_content_sha256
    )
    assert delta.modifications[0].previous_document_id != (
        delta.modifications[0].current_document_id
    )
    assert delta.invalidated_chunk_ids == tuple(
        sorted(chunk.chunk_id for chunk in before.chunks)
    )
    assert delta.added_chunk_ids == tuple(
        sorted(chunk.chunk_id for chunk in after.chunks)
    )


def test_delta_rejects_wrong_starting_snapshot(tmp_path: Path) -> None:
    previous_documents, current_documents = _transition(tmp_path / "documents")
    previous = build_corpus_snapshot(CONFIGURATION, previous_documents)
    current = build_corpus_snapshot(CONFIGURATION, current_documents)
    delta = plan_corpus_delta(previous, current)

    with pytest.raises(ValueError, match="does not start"):
        apply_corpus_delta(current, delta, CONFIGURATION, current_documents)


def test_noop_delta_has_equal_identities_and_cannot_claim_changes(
    tmp_path: Path,
) -> None:
    root = tmp_path / "documents"
    root.mkdir()
    source = root / "stable.txt"
    _write(source, "stable")
    snapshot = build_corpus_snapshot(CONFIGURATION, (_document(source, root),))

    delta = plan_corpus_delta(snapshot, snapshot)

    assert delta.is_noop
    assert delta.previous_snapshot_id == delta.current_snapshot_id
    with pytest.raises(ValueError, match="no-op corpus delta"):
        replace(delta, added_document_ids=(snapshot.documents[0].document_id,))
