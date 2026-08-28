# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("faiss")

from bijux_canon_index.application import (
    AdmittedIndexChunk,
    IndexBuildLimits,
    IndexCompatibility,
    IndexQueryChannel,
    IndexQueryRequest,
    IndexService,
)
from bijux_canon_index.domain.metadata_filters import MetadataFilter
from bijux_canon_index.infra.adapters.faiss.hnsw import HnswParameters


def _chunks() -> tuple[AdmittedIndexChunk, ...]:
    return (
        AdmittedIndexChunk(
            "chunk-a",
            "paper-a",
            0,
            "Ancient DNA evidence.",
            (1.0, 0.0, 0.0),
            {"source_id": "paper-a", "language": "en"},
        ),
        AdmittedIndexChunk(
            "chunk-b",
            "paper-b",
            0,
            "Genomic contamination.",
            (0.7, 0.7, 0.0),
            {"source_id": "paper-b", "language": "en"},
        ),
        AdmittedIndexChunk(
            "chunk-c",
            "paper-c",
            0,
            "Proteomic evidence.",
            (0.0, 1.0, 0.0),
            {"source_id": "paper-c", "language": "en"},
        ),
    )


def _service(path: Path) -> IndexService:
    service = IndexService(
        path,
        compatibility=IndexCompatibility("sha256:model", 3),
    )
    service.build(
        _chunks(),
        snapshot_artifact_id="sha256:snapshot",
        model_lock_artifact_id="sha256:model",
        limits=IndexBuildLimits(10, 10_000, 10_000, 10_000),
        hnsw_parameters=HnswParameters(m=2, ef_construction=8, ef_search=8, seed=7),
        activate=True,
    )
    return service


def _request(metadata_filter: MetadataFilter | None = None) -> IndexQueryRequest:
    return IndexQueryRequest(
        channel=IndexQueryChannel.dense_hnsw,
        query_vector=(1.0, 0.1, 0.0),
        top_k=2,
        metadata_filter=metadata_filter,
    )


def test_exact_witness_binds_query_filter_generation_and_ranking(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path / "registry")
    witness = service.exact_witness(_request())

    assert witness.backend == "faiss-flat-ip"
    assert witness.metric == "inner_product"
    assert witness.normalization == "l2-float32-v1"
    assert [candidate.rank for candidate in witness.candidates] == [1, 2]
    assert witness.candidates[0].chunk_id == "chunk-a"
    assert len(witness.query_vector_sha256) == 64
    assert len(witness.filter_sha256) == 64
    assert len(witness.result_sha256) == 64
    assert len(witness.candidate_order_sha256) == 64

    restarted = _service(tmp_path / "other-registry")
    assert restarted.exact_witness(_request()) == witness


def test_exact_witness_identity_changes_with_filter_and_refuses_lexical(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path / "registry")
    unfiltered = service.exact_witness(_request())
    filtered = service.exact_witness(_request(MetadataFilter(source_ids=("paper-b",))))

    assert filtered.witness_id != unfiltered.witness_id
    assert [candidate.chunk_id for candidate in filtered.candidates] == ["chunk-b"]
    assert not hasattr(filtered.candidates[0], "text")
    assert not hasattr(filtered.candidates[0], "metadata")

    with pytest.raises(ValueError, match="dense query"):
        service.exact_witness(
            IndexQueryRequest(
                channel=IndexQueryChannel.lexical,
                query_text="evidence",
                top_k=2,
            )
        )
