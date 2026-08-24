# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from threading import Event, Thread

import pytest

from bijux_canon_ingest import (
    CorpusSnapshot,
    CorpusSnapshotConfiguration,
    CorpusSnapshotDocument,
    DiscoveredSource,
    PublishedCorpusSnapshot,
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
from bijux_canon_ingest.application.corpus_publication import (
    read_published_snapshot_reuse_bundles,
)
from bijux_canon_ingest.application.snapshot_reuse import (
    restore_published_corpus_snapshot,
)
from bijux_canon_ingest.domain.semantic_chunking import SemanticChunkingPolicy
from bijux_canon_ingest.infra import corpus_snapshot_store
from bijux_canon_ingest.infra.corpus_snapshot_store import PublicationCheckpoint


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
        + b"\n"
    )


def _snapshot(
    source_root: Path,
    text: str,
    *,
    chunking_policy: SemanticChunkingPolicy | None = None,
) -> CorpusSnapshot:
    chunking_policy = chunking_policy or SemanticChunkingPolicy()
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
    chunks = chunk_document_mappings(document, mappings, policy=chunking_policy)
    snapshot_document = CorpusSnapshotDocument(
        admission,
        document,
        metadata,
        mappings,
        chunks,
    )
    return build_corpus_snapshot(
        CorpusSnapshotConfiguration(
            corpus_name="publication-test",
            chunking_policy=chunking_policy,
        ),
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
    assert published.relation_sha256 is not None
    assert published.source_object_count == 1
    assert published.derived_object_count > 1
    assert published.manifest()["schema_version"] == (
        "bijux.canon.ingest.corpus_publication.v2"
    )


def test_published_snapshot_restores_exact_typed_members_after_restart(
    tmp_path: Path,
) -> None:
    sources = tmp_path / "sources"
    store = tmp_path / "store"
    snapshot = _snapshot(sources, "Restart restoration preserves exact text.")
    publication = publish_corpus_snapshot(store, snapshot)

    restarted_publication = read_published_corpus_snapshot(store)
    assert restarted_publication == publication
    assert restarted_publication is not None
    restored = restore_published_corpus_snapshot(
        restarted_publication,
        read_published_snapshot_reuse_bundles(store),
        root_path=sources,
    )

    assert restored == snapshot
    assert restored.canonical_bytes == snapshot.canonical_bytes
    assert restored.documents[0].document == snapshot.documents[0].document


def test_sentence_boundary_policy_restores_after_restart(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    store = tmp_path / "store"
    policy = SemanticChunkingPolicy(boundary_strategy="sentence")
    snapshot = _snapshot(
        sources,
        "Sentence-aware restoration preserves its explicit policy.",
        chunking_policy=policy,
    )
    publication = publish_corpus_snapshot(store, snapshot)

    restored = restore_published_corpus_snapshot(
        publication,
        read_published_snapshot_reuse_bundles(store),
        root_path=sources,
    )

    assert restored == snapshot
    assert restored.configuration.chunking_policy == policy


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
    publish_corpus_snapshot(store, previous)
    current = _snapshot(sources, "Current complete snapshot.")
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


@pytest.mark.parametrize("checkpoint", tuple(PublicationCheckpoint))
def test_failure_before_activation_preserves_previous_and_retry_is_idempotent(
    tmp_path: Path,
    checkpoint: PublicationCheckpoint,
) -> None:
    sources = tmp_path / "sources"
    store_root = tmp_path / "store"
    previous = _snapshot(sources, "Previously admitted content.")
    published_previous = publish_corpus_snapshot(store_root, previous)
    current = _snapshot(sources, f"Candidate interrupted at {checkpoint.value}.")

    def fail(selected: PublicationCheckpoint) -> None:
        if selected is checkpoint:
            raise RuntimeError(f"injected:{selected.value}")

    with pytest.raises(RuntimeError, match=f"injected:{checkpoint.value}"):
        corpus_snapshot_store.CorpusSnapshotStore(
            store_root,
            fault_hook=fail,
        ).publish(current)

    assert read_published_corpus_snapshot(store_root) == published_previous
    published_current = publish_corpus_snapshot(store_root, current)
    assert read_published_corpus_snapshot(store_root) == published_current
    assert publish_corpus_snapshot(store_root, current) == published_current


def test_content_objects_are_reachable_and_repeat_publication_adds_nothing(
    tmp_path: Path,
) -> None:
    sources = tmp_path / "sources"
    store = tmp_path / "store"
    snapshot = _snapshot(sources, "Reachable source and derived content.")
    published = publish_corpus_snapshot(store, snapshot)
    relation_path = store / "relations" / f"{published.generation_name}.json"
    relation = json.loads(relation_path.read_bytes())
    entries = relation["objects"]
    object_paths = {
        store / "objects" / entry["object_sha256"][:2] / entry["object_sha256"][2:]
        for entry in entries
    }

    assert len(entries) == (
        published.source_object_count + published.derived_object_count
    )
    assert all(path.is_file() and not path.is_symlink() for path in object_paths)
    assert all(
        hashlib.sha256(path.read_bytes()).hexdigest()
        == f"{path.parent.name}{path.name}"
        for path in object_paths
    )
    before = {path: path.read_bytes() for path in object_paths}
    (sources / "research.txt").unlink()

    assert publish_corpus_snapshot(store, snapshot) == published
    assert {path: path.read_bytes() for path in object_paths} == before


def test_prior_generation_remains_byte_identical_after_new_activation(
    tmp_path: Path,
) -> None:
    sources = tmp_path / "sources"
    store = tmp_path / "store"
    previous = publish_corpus_snapshot(
        store,
        _snapshot(sources, "Immutable previous generation."),
    )
    previous_generation = store / "generations" / previous.generation_name
    previous_relation = store / "relations" / f"{previous.generation_name}.json"
    before = {
        path.relative_to(store): path.read_bytes()
        for path in (
            previous_generation / "manifest.json",
            previous_generation / "snapshot.json",
            previous_relation,
        )
    }

    current = publish_corpus_snapshot(
        store,
        _snapshot(sources, "New independently activated generation."),
    )

    assert current.snapshot_id != previous.snapshot_id
    assert {relative: (store / relative).read_bytes() for relative in before} == before


def test_source_change_before_publication_is_refused_without_activation(
    tmp_path: Path,
) -> None:
    sources = tmp_path / "sources"
    store = tmp_path / "store"
    snapshot = _snapshot(sources, "Bytes captured by the snapshot.")
    (sources / "research.txt").write_text(
        "Different bytes before publication.",
        encoding="utf-8",
    )

    with pytest.raises(SnapshotPublicationError, match="source changed"):
        publish_corpus_snapshot(store, snapshot)

    assert read_published_corpus_snapshot(store) is None


def test_concurrent_reader_observes_complete_previous_until_activation(
    tmp_path: Path,
) -> None:
    sources = tmp_path / "sources"
    store_root = tmp_path / "store"
    previous = _snapshot(sources, "Concurrent reader previous content.")
    published_previous = publish_corpus_snapshot(store_root, previous)
    current = _snapshot(sources, "Concurrent reader replacement content.")
    before_activation = Event()
    allow_activation = Event()
    outcomes: list[PublishedCorpusSnapshot] = []

    def pause(checkpoint: PublicationCheckpoint) -> None:
        if checkpoint is PublicationCheckpoint.before_activation:
            before_activation.set()
            if not allow_activation.wait(timeout=5):
                raise RuntimeError("concurrent reader did not release activation")

    def publish() -> None:
        outcomes.append(
            corpus_snapshot_store.CorpusSnapshotStore(
                store_root,
                fault_hook=pause,
            ).publish(current)
        )

    worker = Thread(target=publish)
    worker.start()
    assert before_activation.wait(timeout=5)
    assert read_published_corpus_snapshot(store_root) == published_previous
    allow_activation.set()
    worker.join(timeout=5)

    assert not worker.is_alive()
    assert len(outcomes) == 1
    assert read_published_corpus_snapshot(store_root) == outcomes[0]


def test_concurrent_duplicate_publications_share_one_logical_generation(
    tmp_path: Path,
) -> None:
    sources = tmp_path / "sources"
    store = tmp_path / "store"
    snapshot = _snapshot(sources, "Concurrent duplicate publication.")
    outcomes: list[PublishedCorpusSnapshot] = []

    workers = [
        Thread(target=lambda: outcomes.append(publish_corpus_snapshot(store, snapshot)))
        for _ in range(2)
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=5)

    assert all(not worker.is_alive() for worker in workers)
    assert len(outcomes) == 2 and outcomes[0] == outcomes[1]
    assert len(tuple((store / "generations").iterdir())) == 1
    assert len(tuple((store / "relations").iterdir())) == 1


def test_tampered_reachable_object_refuses_active_snapshot(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    store = tmp_path / "store"
    published = publish_corpus_snapshot(
        store,
        _snapshot(sources, "Tamper-evident object publication."),
    )
    relation = json.loads(
        (store / "relations" / f"{published.generation_name}.json").read_bytes()
    )
    source_entry = next(
        entry for entry in relation["objects"] if entry["kind"] == "source-bytes"
    )
    object_path = (
        store
        / "objects"
        / source_entry["object_sha256"][:2]
        / source_entry["object_sha256"][2:]
    )
    object_path.write_bytes(b"tampered")

    with pytest.raises(SnapshotPublicationError, match="object is corrupt"):
        read_published_corpus_snapshot(store)


def test_legacy_manifest_remains_readable_without_relation_objects(
    tmp_path: Path,
) -> None:
    sources = tmp_path / "sources"
    store = tmp_path / "store"
    published = publish_corpus_snapshot(
        store,
        _snapshot(sources, "Legacy publication compatibility."),
    )
    legacy = PublishedCorpusSnapshot(
        snapshot_id=published.snapshot_id,
        canonical_bytes=published.canonical_bytes,
        canonical_sha256=published.canonical_sha256,
    )
    manifest_bytes = _canonical_json(legacy.manifest())
    generation = store / "generations" / legacy.generation_name
    (generation / "manifest.json").write_bytes(manifest_bytes)
    (store / "active.json").write_bytes(manifest_bytes)

    assert read_published_corpus_snapshot(store) == legacy
