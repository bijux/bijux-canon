# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from bijux_canon_ingest import (
    CorpusSnapshot,
    CorpusSnapshotConfiguration,
    CorpusSnapshotDocument,
    DiscoveredSource,
    SnapshotPublicationError,
    admit_source,
    build_corpus_snapshot,
    build_document_span_mappings,
    chunk_document_mappings,
    normalize_source_metadata,
    parse_text,
    publish_corpus_snapshot,
    read_published_corpus_snapshot,
    recover_corpus_snapshot_store,
)
from bijux_canon_ingest.infra import corpus_snapshot_store


def _snapshot(source_root: Path, text: str) -> CorpusSnapshot:
    source_root.mkdir(exist_ok=True)
    source_path = source_root / "research.txt"
    source_path.write_text(text, encoding="utf-8")
    content = source_path.read_bytes()
    source = DiscoveredSource.create(
        root_name="research",
        relative_path="research.txt",
        filesystem_path=source_path,
        content_sha256=hashlib.sha256(content).hexdigest(),
        byte_length=len(content),
        media_type="text/plain",
        is_symlink=False,
    )
    admission = admit_source(source)
    assert admission.admitted and admission.format_id == "text"
    document = parse_text(admission)
    metadata = normalize_source_metadata(source, format_id="text")
    mappings = build_document_span_mappings(content, document)
    chunks = chunk_document_mappings(document, mappings)
    snapshot_document = CorpusSnapshotDocument(
        admission,
        document,
        metadata,
        mappings,
        chunks,
    )
    return build_corpus_snapshot(
        CorpusSnapshotConfiguration(corpus_name="publication-test"),
        (snapshot_document,),
    )


def test_publish_activates_complete_canonical_generation(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path / "sources", "First admitted document.")
    store = tmp_path / "store"

    published = publish_corpus_snapshot(store, snapshot)
    active = read_published_corpus_snapshot(store)

    assert active == published
    assert active is not None
    assert active.canonical_bytes == snapshot.canonical_bytes
    generation = store / "generations" / published.generation_name
    assert (generation / "snapshot.json").read_bytes() == snapshot.canonical_bytes
    assert (generation / "manifest.json").read_bytes() == (
        store / "active.json"
    ).read_bytes()


def test_activation_manifest_is_replaced_last(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _snapshot(tmp_path / "sources", "Manifest ordering evidence.")
    destinations: list[str] = []
    replace = os.replace

    def record_replace(source: str | Path, destination: str | Path) -> None:
        destinations.append(Path(destination).name)
        replace(source, destination)

    monkeypatch.setattr(corpus_snapshot_store.os, "replace", record_replace)

    publish_corpus_snapshot(tmp_path / "store", snapshot)

    assert destinations[-1] == "active.json"


def test_interrupted_activation_preserves_last_admitted_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources = tmp_path / "sources"
    store = tmp_path / "store"
    previous = _snapshot(sources, "Previous admitted snapshot.")
    publish_corpus_snapshot(store, previous)
    current = _snapshot(sources, "Candidate replacement snapshot.")
    replace = os.replace

    def interrupt_activation(source: str | Path, destination: str | Path) -> None:
        if Path(destination).name == "active.json":
            raise OSError("simulated interruption before activation")
        replace(source, destination)

    monkeypatch.setattr(
        corpus_snapshot_store.os,
        "replace",
        interrupt_activation,
    )

    with pytest.raises(OSError, match="simulated interruption"):
        publish_corpus_snapshot(store, current)

    admitted = read_published_corpus_snapshot(store)
    assert admitted is not None
    assert admitted.snapshot_id == previous.snapshot_id


def test_recovery_rejects_partial_generation_and_restores_previous(
    tmp_path: Path,
) -> None:
    sources = tmp_path / "sources"
    store = tmp_path / "store"
    previous = _snapshot(sources, "Previous complete snapshot.")
    current = _snapshot(sources, "Current complete snapshot.")
    publish_corpus_snapshot(store, previous)
    published = publish_corpus_snapshot(store, current)
    (store / "generations" / published.generation_name / "snapshot.json").unlink()
    abandoned = store / "staging" / "abandoned-generation"
    abandoned.mkdir()
    (abandoned / "partial").write_bytes(b"partial")

    with pytest.raises(SnapshotPublicationError, match="incomplete"):
        read_published_corpus_snapshot(store)

    recovery = recover_corpus_snapshot_store(store)

    assert recovery.status == "recovered"
    assert recovery.removed_staging_entries == 1
    assert recovery.snapshot is not None
    assert recovery.snapshot.snapshot_id == previous.snapshot_id
    assert read_published_corpus_snapshot(store) == recovery.snapshot
