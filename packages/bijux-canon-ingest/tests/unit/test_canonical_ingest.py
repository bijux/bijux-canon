# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from bijux_canon_ingest.application import canonical_ingest
from bijux_canon_ingest.application.canonical_ingest import (
    CanonicalIngestRequest,
    CanonicalIngestRuntime,
    assemble_corpus_snapshot_manifest,
    ingest_corpus,
    prepare_corpus,
)
from bijux_canon_ingest.application.source_mapping import ParsedSourceDocument
from bijux_canon_ingest.domain.corpus_snapshot import CorpusSnapshotConfiguration
from bijux_canon_ingest.domain.source_admission import AdmissionResult

REAL_CORPUS = Path(__file__).parents[4] / "examples/document-formats/corpus"
RESEARCH_CORPUS = (
    Path(__file__).parents[4] / "examples/ancient-dna-research/corpus/sources"
)
RESEARCH_LOCK = RESEARCH_CORPUS.parents[1] / "corpus.lock.json"
FORMAT_PARSER_TITLES = {
    "docx": "Guide to Preparing an Assurance Review Report",
    "html": (
        "Ancient RNA from Late Pleistocene permafrost and historical canids "
        "shows tissue-specific transcriptome survival"
    ),
    "jats": (
        "Ancient RNA from Late Pleistocene permafrost and historical canids "
        "shows tissue-specific transcriptome survival"
    ),
    "markdown": "Select a storage driver",
    "pdf-digital": (
        "Ancient RNA from Late Pleistocene permafrost and historical canids "
        "shows tissue-specific transcriptome survival"
    ),
    "text": "HTTP Semantics",
}


def test_canonical_runtime_ingests_real_format_corpus(tmp_path: Path) -> None:
    result = ingest_corpus(
        CanonicalIngestRequest(
            root_path=REAL_CORPUS,
            root_name="real-formats",
            configuration=CorpusSnapshotConfiguration(corpus_name="real-formats"),
            publication_root=tmp_path / "published",
        )
    )

    manifest = result.manifest()
    assert manifest["formats"] == {
        "docx": 1,
        "html": 1,
        "jats": 1,
        "markdown": 1,
        "pdf-digital": 1,
        "text": 1,
    }
    assert manifest["document_count"] == 6
    assert manifest["corpus_lock"] == {
        "discovery": "automatic",
        "lock_identity_sha256": (
            "9a0b63f5222b44bb571e8c2ed95b0a1b2abb1e508ac0d6e2ff5aae2fba6366c9"
        ),
        "schema_version": "bijux.canon.parser_source_lock.v1",
        "source_count": 7,
        "status": "verified",
    }
    assert manifest["ocr_required_count"] == 1
    assert isinstance(manifest["chunk_count"], int)
    assert manifest["chunk_count"] > 0
    assert result.publication is not None
    assert result.publication.snapshot_id == result.snapshot.snapshot_id
    jats = next(
        document
        for document in result.snapshot.documents
        if document.admission.format_id == "jats"
    )
    assert jats.metadata.title == (
        "Ancient RNA from Late Pleistocene permafrost and historical canids "
        "shows tissue-specific transcriptome survival"
    )
    assert jats.metadata.authors[0] == "Oliver Smith"
    assert jats.metadata.license_expression == "CC-BY-4.0"
    assert {record.source for record in jats.metadata.provenance_records} >= {
        "corpus_lock",
        "acquisition_receipt",
        "embedded_parser",
    }


def test_real_format_publication_reuses_every_parser_after_restart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = CanonicalIngestRequest(
        root_path=REAL_CORPUS,
        root_name="real-formats",
        configuration=CorpusSnapshotConfiguration(corpus_name="real-formats"),
        publication_root=tmp_path / "published",
    )
    initial = CanonicalIngestRuntime().ingest(request)
    assert initial.disposition == "initial"
    parse = canonical_ingest._parse
    parse_calls: list[str] = []

    def recording_parse(admission: AdmissionResult) -> ParsedSourceDocument:
        parse_calls.append(admission.source.relative_path)
        return parse(admission)

    monkeypatch.setattr(canonical_ingest, "_parse", recording_parse)

    unchanged = CanonicalIngestRuntime().ingest(request)

    assert parse_calls == []
    assert unchanged.disposition == "unchanged"
    assert unchanged.snapshot.snapshot_id == initial.snapshot.snapshot_id
    assert unchanged.snapshot.canonical_bytes == initial.snapshot.canonical_bytes
    assert unchanged.delta is not None
    assert unchanged.delta.previous_snapshot_id == unchanged.delta.current_snapshot_id


def test_canonical_runtime_merges_parser_metadata_for_every_real_format() -> None:
    preparation = prepare_corpus(
        CanonicalIngestRequest(
            root_path=REAL_CORPUS,
            root_name="real-formats",
            configuration=CorpusSnapshotConfiguration(corpus_name="real-formats"),
        )
    )
    assert {document.admission.format_id for document in preparation.documents} == set(
        FORMAT_PARSER_TITLES
    )
    for document in preparation.documents:
        format_id = document.admission.format_id
        assert format_id is not None
        parser_records = [
            record
            for record in document.metadata.provenance_records
            if record.source == "embedded_parser"
        ]
        parser_titles = [
            value.normalized_value
            for value in document.metadata.raw_values
            if value.field == "title" and value.source == "embedded_parser"
        ]
        assert len(parser_records) == 1, format_id
        assert parser_records[0].source_content_sha256 == (
            document.admission.source.content_sha256
        )
        assert parser_records[0].source_byte_length == (
            document.admission.source.byte_length
        )
        assert parser_titles == [FORMAT_PARSER_TITLES[format_id]], format_id


def test_unlocked_real_formats_select_parser_titles(tmp_path: Path) -> None:
    root = tmp_path / "unlocked-formats"
    shutil.copytree(REAL_CORPUS, root)
    preparation = prepare_corpus(
        CanonicalIngestRequest(
            root_path=root,
            root_name="unlocked-formats",
            configuration=CorpusSnapshotConfiguration(corpus_name="unlocked-formats"),
        )
    )

    assert preparation.corpus_lock is None
    for document in preparation.documents:
        format_id = document.admission.format_id
        assert format_id is not None
        assert document.metadata.title == FORMAT_PARSER_TITLES[format_id]
        selected_title = next(
            value
            for value in document.metadata.selected_values
            if value.field == "title"
        )
        assert selected_title.source == "embedded_parser", format_id
        assert all(
            record.source != "filename_fallback"
            for record in document.metadata.provenance_records
        )


def test_canonical_runtime_automatically_uses_research_corpus_lock() -> None:
    preparation = prepare_corpus(
        CanonicalIngestRequest(
            root_path=RESEARCH_CORPUS,
            root_name="ancient-dna-research",
            configuration=CorpusSnapshotConfiguration(
                corpus_name="ancient-dna-research"
            ),
        )
    )

    assert len(preparation.documents) == 8
    assert not preparation.rejections
    assert preparation.corpus_lock is not None
    assert preparation.corpus_lock.lock_identity_sha256 == (
        "8bcb928cc8a6ee419599c4672c37176949ddd25e99b0963e5522e0e0688a66ba"
    )
    assert {
        (document.metadata.title, document.metadata.doi)
        for document in preparation.documents
    } == {
        (
            "Ancient RNA from Late Pleistocene permafrost and historical canids "
            "shows tissue-specific transcriptome survival",
            "10.1371/journal.pbio.3000166",
        ),
        (
            "Cryptic Contamination and Phylogenetic Nonsense",
            "10.1371/journal.pone.0002316",
        ),
        (
            "To Clone or Not To Clone: Method Analysis for Retrieving Consensus "
            "Sequences In Ancient DNA Samples",
            "10.1371/journal.pone.0021247",
        ),
        (
            "Fragmentation of Contaminant and Endogenous DNA in Ancient Samples "
            "Determined by Shotgun Sequencing; Prospects for Human Palaeogenomics",
            "10.1371/journal.pone.0024161",
        ),
        (
            "Absence of Ancient DNA in Sub-Fossil Insect Inclusions Preserved in "
            "‘Anthropocene’ Colombian Copal",
            "10.1371/journal.pone.0073150",
        ),
        (
            "Optimal Ancient DNA Yields from the Inner Ear Part of the Human "
            "Petrous Bone",
            "10.1371/journal.pone.0129102",
        ),
        (
            "DNA from resin-embedded organisms: Past, present and future",
            "10.1371/journal.pone.0239521",
        ),
        (
            "Uncovering the genomic and metagenomic research potential in old "
            "ethanol-preserved snakes",
            "10.1371/journal.pone.0256353",
        ),
    }
    lock = json.loads(RESEARCH_LOCK.read_text(encoding="utf-8"))
    locked_by_sha256 = {source["sha256"]: source for source in lock["sources"]}
    assert len(locked_by_sha256) == 8
    for document in preparation.documents:
        expected = locked_by_sha256[document.admission.source.content_sha256]
        metadata = document.metadata
        assert metadata.title == expected["title"]
        assert metadata.doi == expected["doi"]
        assert metadata.authors == tuple(expected["authors"])
        assert metadata.journal == expected["journal"]
        assert metadata.license_expression == "CC-BY-4.0"
        assert metadata.license_url == expected["license"]["url"]
        assert any(
            value.field == "license_expression"
            and value.source == "corpus_lock"
            and value.value == expected["license"]["expression"]
            for value in metadata.raw_values
        )
        assert {record.source for record in metadata.provenance_records} >= {
            "corpus_lock",
            "acquisition_receipt",
            "embedded_parser",
        }


def test_canonical_runtime_result_is_deterministic() -> None:
    request = CanonicalIngestRequest(
        root_path=REAL_CORPUS,
        root_name="real-formats",
        configuration=CorpusSnapshotConfiguration(corpus_name="real-formats"),
    )

    assert ingest_corpus(request).manifest() == ingest_corpus(request).manifest()


def test_published_ingest_reuses_unchanged_work_and_audits_file_deltas(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "corpus"
    root.mkdir()
    stable = root / "stable.txt"
    changing = root / "changing.txt"
    stable.write_text("Stable title\n\nStable evidence.", encoding="utf-8")
    changing.write_text("Changing title\n\nOld evidence.", encoding="utf-8")
    publication_root = tmp_path / "published"
    request = CanonicalIngestRequest.for_directory(
        root_path=root,
        root_name="incremental",
        corpus_name="incremental",
        publication_root=publication_root,
    )
    parse_calls: list[str] = []
    parse = canonical_ingest._parse

    def recording_parse(admission: AdmissionResult) -> ParsedSourceDocument:
        parse_calls.append(admission.source.relative_path)
        return parse(admission)

    monkeypatch.setattr(canonical_ingest, "_parse", recording_parse)
    initial = CanonicalIngestRuntime().ingest(request)
    assert initial.publication is not None
    initial_generation = (
        publication_root
        / "generations"
        / initial.publication.generation_name
        / "snapshot.json"
    )
    initial_bytes = initial_generation.read_bytes()

    unchanged = CanonicalIngestRuntime().ingest(request)
    assert parse_calls == ["changing.txt", "stable.txt"]
    assert unchanged.disposition == "unchanged"
    assert unchanged.snapshot.snapshot_id == initial.snapshot.snapshot_id
    assert unchanged.delta is not None
    assert not unchanged.delta.added_document_ids
    assert not unchanged.delta.deleted_document_ids
    assert not unchanged.delta.modifications
    assert not unchanged.delta.renames

    changing.write_text("Changing title\n\nNew evidence.", encoding="utf-8")
    modified = CanonicalIngestRuntime().ingest(request)
    assert parse_calls[-1:] == ["changing.txt"]
    assert modified.disposition == "changed"
    assert modified.delta is not None and len(modified.delta.modifications) == 1

    added_path = root / "added.txt"
    added_path.write_text("Added title\n\nAdded evidence.", encoding="utf-8")
    added = CanonicalIngestRuntime().ingest(request)
    assert parse_calls[-1:] == ["added.txt"]
    assert added.delta is not None and len(added.delta.added_document_ids) == 1

    added_path.unlink()
    deleted = CanonicalIngestRuntime().ingest(request)
    assert parse_calls[-1:] == ["added.txt"]
    assert deleted.delta is not None and len(deleted.delta.deleted_document_ids) == 1

    renamed = root / "stable-renamed.txt"
    stable.rename(renamed)
    renamed_result = CanonicalIngestRuntime().ingest(request)
    assert parse_calls[-1:] == ["added.txt"]
    assert renamed_result.delta is not None
    assert len(renamed_result.delta.renames) == 1
    assert renamed_result.delta.renames[0].previous_relative_path == "stable.txt"
    assert renamed_result.delta.renames[0].current_relative_path == (
        "stable-renamed.txt"
    )
    assert initial_generation.read_bytes() == initial_bytes


def test_parser_contract_change_reparses_only_affected_format(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "corpus"
    root.mkdir()
    (root / "evidence.txt").write_text("Text title\n\nText evidence.", encoding="utf-8")
    (root / "evidence.md").write_text(
        "# Markdown title\n\nMarkdown evidence.", encoding="utf-8"
    )
    request = CanonicalIngestRequest.for_directory(
        root_path=root,
        root_name="parser-contract",
        corpus_name="parser-contract",
        publication_root=tmp_path / "published",
    )
    initial = CanonicalIngestRuntime().ingest(request)
    assert initial.disposition == "initial"
    original_identity = canonical_ingest._parser_identity
    original_parse = canonical_ingest._parse
    parse_calls: list[str] = []

    def changed_identity(format_id: str) -> tuple[str, str, str]:
        name, version, schema = original_identity(format_id)
        return (
            (name, f"{version}-changed", schema)
            if format_id == "text"
            else (
                name,
                version,
                schema,
            )
        )

    def recording_parse(admission: AdmissionResult) -> ParsedSourceDocument:
        parse_calls.append(admission.source.relative_path)
        return original_parse(admission)

    monkeypatch.setattr(canonical_ingest, "_parser_identity", changed_identity)
    monkeypatch.setattr(canonical_ingest, "_parse", recording_parse)

    result = CanonicalIngestRuntime().ingest(request)

    assert parse_calls == ["evidence.txt"]
    assert result.disposition == "unchanged"
    assert result.delta is not None and not result.delta.modifications


def test_preparation_and_snapshot_are_distinct_restart_safe_operations() -> None:
    request = CanonicalIngestRequest(
        root_path=REAL_CORPUS,
        root_name="real-formats",
        configuration=CorpusSnapshotConfiguration(corpus_name="real-formats"),
    )

    preparation = prepare_corpus(request)
    preparation_manifest = preparation.manifest()
    persisted_preparation = json.loads(json.dumps(preparation_manifest))
    snapshot_manifest = assemble_corpus_snapshot_manifest(persisted_preparation)

    assert preparation_manifest["schema_version"] == (
        "bijux.canon.ingest.corpus_preparation.v2"
    )
    assert snapshot_manifest == preparation.snapshot().manifest()
    assert snapshot_manifest["snapshot_id"] != preparation_manifest["preparation_id"]


def test_snapshot_assembly_accepts_legacy_preparation_without_lock_summary() -> None:
    request = CanonicalIngestRequest(
        root_path=REAL_CORPUS,
        root_name="real-formats",
        configuration=CorpusSnapshotConfiguration(corpus_name="real-formats"),
    )
    preparation = prepare_corpus(request)
    legacy = preparation.manifest()
    legacy["schema_version"] = "bijux.canon.ingest.corpus_preparation.v1"
    legacy.pop("corpus_lock")
    legacy.pop("preparation_id")
    encoded = json.dumps(
        legacy,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    legacy["preparation_id"] = f"sha256:{hashlib.sha256(encoded).hexdigest()}"

    assert (
        assemble_corpus_snapshot_manifest(legacy) == preparation.snapshot().manifest()
    )


def test_snapshot_assembly_rejects_tampered_preparation() -> None:
    request = CanonicalIngestRequest(
        root_path=REAL_CORPUS,
        root_name="real-formats",
        configuration=CorpusSnapshotConfiguration(corpus_name="real-formats"),
    )
    preparation = prepare_corpus(request).manifest()
    preparation["configuration_sha256"] = "sha256:" + "0" * 64

    with pytest.raises(ValueError, match="corpus preparation identity is invalid"):
        assemble_corpus_snapshot_manifest(preparation)
