# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bijux_canon_ingest.application.canonical_ingest import (
    CanonicalIngestRequest,
    assemble_corpus_snapshot_manifest,
    ingest_corpus,
    prepare_corpus,
)
from bijux_canon_ingest.domain.corpus_snapshot import CorpusSnapshotConfiguration

REAL_CORPUS = Path(__file__).parents[4] / "examples/document-formats/corpus"
RESEARCH_CORPUS = (
    Path(__file__).parents[4] / "examples/ancient-dna-research/corpus/sources"
)


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
    }


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


def test_canonical_runtime_result_is_deterministic() -> None:
    request = CanonicalIngestRequest(
        root_path=REAL_CORPUS,
        root_name="real-formats",
        configuration=CorpusSnapshotConfiguration(corpus_name="real-formats"),
    )

    assert ingest_corpus(request).manifest() == ingest_corpus(request).manifest()


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
