# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

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
    assert manifest["ocr_required_count"] == 1
    assert isinstance(manifest["chunk_count"], int)
    assert manifest["chunk_count"] > 0
    assert result.publication is not None
    assert result.publication.snapshot_id == result.snapshot.snapshot_id


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
        "bijux.canon.ingest.corpus_preparation.v1"
    )
    assert snapshot_manifest == preparation.snapshot().manifest()
    assert snapshot_manifest["snapshot_id"] != preparation_manifest["preparation_id"]


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
