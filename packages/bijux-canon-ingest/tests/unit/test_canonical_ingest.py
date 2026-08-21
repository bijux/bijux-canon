# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

from bijux_canon_ingest.application.canonical_ingest import (
    CanonicalIngestRequest,
    ingest_corpus,
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
