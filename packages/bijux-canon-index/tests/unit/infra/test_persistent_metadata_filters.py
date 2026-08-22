# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Cross-channel persistence tests for typed metadata filters."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

pytest.importorskip("faiss")

from bijux_canon_index.domain.metadata_filters import (
    MetadataFilter,
    MetadataOperator,
    UserMetadataPredicate,
)
from bijux_canon_index.infra.adapters.faiss.exact import (
    DenseVectorRecord,
    FaissExactIndex,
)
from bijux_canon_index.infra.adapters.faiss.hnsw import (
    FaissHnswIndex,
    HnswParameters,
)
from bijux_canon_index.infra.adapters.sqlite.lexical import (
    LexicalChunk,
    SQLiteLexicalIndex,
)


def _metadata(source_id: str, *, target: bool) -> dict[str, object]:
    return {
        "source_id": source_id,
        "doi": f"10.1371/{source_id}",
        "path": f"objects/{source_id}/article.xml",
        "format": "jats" if target else "pdf",
        "section": "results" if target else "methods",
        "date": "2021-09-01" if target else "2019-03-02",
        "tags": ("ancient-dna", "reviewed") if target else ("proteomics",),
        "language": "en" if target else "sv",
        "quality": 0.95 if target else 0.4,
        "license": "CC-BY-4.0" if target else "CC0-1.0",
    }


def _spec() -> MetadataFilter:
    return MetadataFilter(
        source_ids=("plos-pone-0256353",),
        dois=("10.1371/plos-pone-0256353",),
        paths=("objects/plos-pone-0256353/article.xml",),
        formats=("jats",),
        sections=("results",),
        date_from=date(2021, 1, 1),
        date_to=date(2021, 12, 31),
        tags=("ancient-dna", "reviewed"),
        languages=("en",),
        user=(
            UserMetadataPredicate("quality", MetadataOperator.greater_or_equal, 0.9),
            UserMetadataPredicate("license", MetadataOperator.equal, "CC-BY-4.0"),
        ),
    )


def test_typed_filter_is_identical_across_persistent_channels(tmp_path: Path) -> None:
    metadata_a = _metadata("plos-pone-0256353", target=True)
    metadata_b = _metadata("plos-pone-0002316", target=False)
    lexical_chunks = (
        LexicalChunk("chunk-b", "document-b", 0, "Ancient DNA evidence", metadata_a),
        LexicalChunk("chunk-a", "document-a", 0, "Ancient DNA evidence", metadata_b),
    )
    dense_records = (
        DenseVectorRecord("chunk-b", (0.9, 0.1, 0.0), metadata_a),
        DenseVectorRecord("chunk-a", (1.0, 0.0, 0.0), metadata_b),
    )
    lexical_path = tmp_path / "lexical.sqlite"
    exact_path = tmp_path / "exact.sqlite"
    hnsw_path = tmp_path / "hnsw.sqlite"
    with SQLiteLexicalIndex.build(lexical_path, lexical_chunks):
        pass
    with FaissExactIndex.build(
        exact_path, dense_records, model_lock_artifact_id="model"
    ):
        pass
    with FaissHnswIndex.build(
        hnsw_path,
        dense_records,
        model_lock_artifact_id="model",
        parameters=HnswParameters(m=2, ef_construction=8, ef_search=8),
    ):
        pass

    with (
        SQLiteLexicalIndex(lexical_path) as lexical,
        FaissExactIndex(exact_path) as exact,
        FaissHnswIndex(hnsw_path) as hnsw,
    ):
        result_sets = (
            [
                result.chunk.chunk_id
                for result in lexical.query(
                    "ancient DNA", metadata_filter=_spec(), top_k=1
                )
            ],
            [
                result.chunk_id
                for result in exact.query(
                    (1.0, 0.0, 0.0), metadata_filter=_spec(), top_k=1
                )
            ],
            [
                result.chunk_id
                for result in hnsw.query(
                    (1.0, 0.0, 0.0), metadata_filter=_spec(), top_k=1
                )
            ],
        )

    assert result_sets == (["chunk-b"], ["chunk-b"], ["chunk-b"])


def test_typed_and_legacy_filters_cannot_be_combined(tmp_path: Path) -> None:
    path = tmp_path / "exact.sqlite"
    record = DenseVectorRecord(
        "chunk-a", (1.0, 0.0), _metadata("plos-pone-0256353", target=True)
    )
    with FaissExactIndex.build(
        path, (record,), model_lock_artifact_id="model"
    ) as exact:
        with pytest.raises(ValueError, match="mutually exclusive"):
            exact.query((1.0, 0.0), filters={"language": "en"}, metadata_filter=_spec())
