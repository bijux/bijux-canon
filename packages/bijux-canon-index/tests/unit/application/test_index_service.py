# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for the canonical immutable index application service."""

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
    LexicalIndexChunk,
    LexicalIndexLimits,
    build_lexical_index_segment,
)
from bijux_canon_index.contracts.authz import RetrievalAuthorizationScope
from bijux_canon_index.domain.metadata_filters import MetadataFilter
from bijux_canon_index.infra.adapters.faiss.hnsw import HnswParameters


def _chunks() -> tuple[AdmittedIndexChunk, ...]:
    return (
        AdmittedIndexChunk(
            "chunk-a",
            "paper-a",
            0,
            "Ancient DNA preserves direct evidence.",
            (1.0, 0.0, 0.0),
            {"source_id": "paper-a", "language": "en"},
        ),
        AdmittedIndexChunk(
            "chunk-b",
            "paper-b",
            0,
            "Genomic contamination constrains interpretation.",
            (0.0, 1.0, 0.0),
            {"source_id": "paper-b", "language": "en"},
        ),
    )


def _service(path: Path) -> IndexService:
    return IndexService(
        path,
        compatibility=IndexCompatibility("sha256:model-lock", 3),
    )


def test_service_owns_build_activate_inspect_verify_query_and_restart(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path / "registry")
    built = service.build(
        _chunks(),
        snapshot_artifact_id="sha256:snapshot",
        model_lock_artifact_id="sha256:model-lock",
        limits=IndexBuildLimits(10, 10_000, 10_000, 10_000),
        hnsw_parameters=HnswParameters(m=2, ef_construction=8, ef_search=8, seed=17),
    )
    assert built.activation.active is False
    activated = service.activate(built.generation_id)
    assert activated.activation.active is True
    assert service.inspect() == activated
    assert service.verify().integrity.status == "verified"

    lexical = service.query(
        IndexQueryRequest(
            channel=IndexQueryChannel.lexical,
            query_text="ancient DNA",
            top_k=1,
        )
    )
    exact = service.query(
        IndexQueryRequest(
            channel=IndexQueryChannel.dense_exact,
            query_vector=(1.0, 0.0, 0.0),
            top_k=1,
        )
    )
    hnsw = service.query(
        IndexQueryRequest(
            channel=IndexQueryChannel.dense_hnsw,
            query_vector=(1.0, 0.0, 0.0),
            top_k=1,
            metadata_filter=MetadataFilter(source_ids=("paper-a",)),
        )
    )
    assert lexical.hits[0].chunk_id == "chunk-a"
    assert exact.hits[0].chunk_id == "chunk-a"
    assert hnsw.hits[0].chunk_id == "chunk-a"
    assert {
        lexical.hits[0].source_text_sha256,
        exact.hits[0].source_text_sha256,
        hnsw.hits[0].source_text_sha256,
    } == {lexical.hits[0].source_text_sha256}
    assert not tuple(service.registry_root.glob(".generation-building-*"))

    restarted = _service(service.registry_root)
    assert restarted.inspect() == activated
    assert (
        restarted.query(
            IndexQueryRequest(
                channel=IndexQueryChannel.dense_exact,
                query_vector=(1.0, 0.0, 0.0),
                top_k=1,
            )
        )
        == exact
    )


def test_query_request_refuses_mixed_missing_and_unbounded_inputs() -> None:
    with pytest.raises(ValueError, match="query vector"):
        IndexQueryRequest(
            channel=IndexQueryChannel.lexical,
            query_text="evidence",
            query_vector=(1.0,),
            top_k=1,
        )
    with pytest.raises(ValueError, match="require a query vector"):
        IndexQueryRequest(channel=IndexQueryChannel.dense_exact, top_k=1)
    with pytest.raises(ValueError, match="between 1 and 1000"):
        IndexQueryRequest(
            channel=IndexQueryChannel.lexical,
            query_text="evidence",
            top_k=1001,
        )


def test_retrieval_scope_filters_every_backend_before_limit_and_survives_restart(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path / "scoped-registry")
    report = service.build(
        (
            AdmittedIndexChunk(
                "chunk-a",
                "paper-a",
                0,
                "Ancient DNA evidence",
                (1.0, 0.0, 0.0),
                {"source_id": "paper-a", "path": "paper-a/article.xml"},
            ),
            AdmittedIndexChunk(
                "chunk-b",
                "paper-b",
                0,
                "Ancient DNA evidence",
                (0.9, 0.1, 0.0),
                {"source_id": "paper-b", "path": "paper-b/article.xml"},
            ),
        ),
        snapshot_artifact_id="sha256:snapshot",
        model_lock_artifact_id="sha256:model-lock",
        limits=IndexBuildLimits(10, 10_000, 10_000, 10_000),
        hnsw_parameters=HnswParameters(m=2, ef_construction=8, ef_search=8, seed=17),
        activate=True,
    )
    scope = RetrievalAuthorizationScope(
        generation_ids=(report.generation_id,),
        source_ids=("paper-b",),
        actor="researcher",
    )
    requests = (
        IndexQueryRequest(
            IndexQueryChannel.lexical,
            1,
            query_text="ancient DNA",
            authorization_scope=scope,
        ),
        IndexQueryRequest(
            IndexQueryChannel.dense_exact,
            1,
            query_vector=(1.0, 0.0, 0.0),
            authorization_scope=scope,
        ),
        IndexQueryRequest(
            IndexQueryChannel.dense_hnsw,
            1,
            query_vector=(1.0, 0.0, 0.0),
            authorization_scope=scope,
        ),
    )

    first = tuple(service.query(request) for request in requests)
    service.close()
    restarted = _service(tmp_path / "scoped-registry")
    repeated = tuple(restarted.query(request) for request in requests)

    assert first == repeated
    assert [[hit.chunk_id for hit in item.hits] for item in first] == [
        ["chunk-b"],
        ["chunk-b"],
        ["chunk-b"],
    ]
    assert {item.authorization_scope_id for item in first} == {scope.artifact_id}
    outside = restarted.query(
        IndexQueryRequest(
            IndexQueryChannel.lexical,
            1,
            query_text="ancient DNA",
            metadata_filter=MetadataFilter(source_ids=("paper-a",)),
            authorization_scope=scope,
        )
    )
    assert outside.hits == ()
    assert outside.authorization_scope_id == scope.artifact_id


def test_failed_build_leaves_no_partial_generation(tmp_path: Path) -> None:
    service = _service(tmp_path / "registry")

    with pytest.raises(ValueError, match="dimension"):
        service.build(
            (
                _chunks()[0],
                AdmittedIndexChunk(
                    "chunk-b",
                    "paper-b",
                    0,
                    "invalid dimension",
                    (1.0, 0.0),
                    {"source_id": "paper-b"},
                ),
            ),
            snapshot_artifact_id="sha256:snapshot",
            model_lock_artifact_id="sha256:model-lock",
            limits=IndexBuildLimits(10, 10_000, 10_000, 10_000),
        )

    assert not tuple(service.registry_root.glob(".generation-building-*"))
    assert not tuple((service.registry_root / "generations").iterdir())


def test_service_admits_and_activates_a_separately_built_lexical_segment(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path / "registry")
    lexical_path = tmp_path / "lexical.sqlite"
    build_lexical_index_segment(
        lexical_path,
        (
            LexicalIndexChunk(
                chunk.chunk_id,
                chunk.document_id,
                chunk.ordinal,
                chunk.text,
                chunk.metadata,
            )
            for chunk in _chunks()
        ),
        limits=LexicalIndexLimits(10, 10_000, 10_000),
    )

    report = service.build_from_lexical(
        lexical_path,
        _chunks(),
        snapshot_artifact_id="sha256:snapshot",
        model_lock_artifact_id="sha256:model-lock",
        limits=IndexBuildLimits(10, 10_000, 10_000, 10_000),
        hnsw_parameters=HnswParameters(m=2, ef_construction=8, ef_search=8, seed=17),
        activate=True,
    )

    assert report.activation.active is True
    assert service.inspect().generation_id == report.generation_id
    assert lexical_path.is_file()
