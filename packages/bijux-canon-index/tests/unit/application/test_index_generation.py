# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for coherent deterministic index generation builds."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

pytest.importorskip("faiss")
pytest.importorskip("numpy")

from bijux_canon_index.application.index_generation import (
    AdmittedIndexChunk,
    IndexBuildLimits,
    IndexGeneration,
    IndexGenerationBuildError,
    LexicalIndexChunk,
    LexicalIndexLimits,
    build_lexical_index_segment,
)
from bijux_canon_index.infra.adapters.faiss.exact import FaissExactIndex
from bijux_canon_index.infra.adapters.faiss.hnsw import HnswParameters


def _chunks() -> tuple[AdmittedIndexChunk, ...]:
    return (
        AdmittedIndexChunk(
            chunk_id="chunk-b",
            document_id="paper-b",
            ordinal=1,
            text="Neanderthal ancestry varies across ancient populations.",
            vector=(0.0, 2.0, 0.0, 0.0),
            metadata={"year": 2024, "section": "results"},
        ),
        AdmittedIndexChunk(
            chunk_id="chunk-a",
            document_id="paper-a",
            ordinal=0,
            text="Ancient DNA preserves direct evidence of population history.",
            vector=(3.0, 0.0, 0.0, 0.0),
            metadata={"year": 2023, "section": "abstract"},
        ),
        AdmittedIndexChunk(
            chunk_id="chunk-c",
            document_id="paper-c",
            ordinal=2,
            text="Genomic contamination estimates constrain interpretation.",
            vector=(0.0, 0.0, 4.0, 0.0),
            metadata={"year": 2022, "section": "methods"},
        ),
    )


def _limits() -> IndexBuildLimits:
    return IndexBuildLimits(
        max_chunks=10,
        max_text_bytes=10_000,
        max_vector_bytes=10_000,
        max_metadata_bytes=10_000,
    )


def _lexical_chunks() -> tuple[LexicalIndexChunk, ...]:
    return tuple(
        LexicalIndexChunk(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            ordinal=chunk.ordinal,
            text=chunk.text,
            metadata=chunk.metadata,
        )
        for chunk in _chunks()
    )


def _lexical_limits() -> LexicalIndexLimits:
    return LexicalIndexLimits(
        max_chunks=10,
        max_text_bytes=10_000,
        max_metadata_bytes=10_000,
    )


def _build(path: Path, chunks: object | None = None) -> IndexGeneration:
    admitted = _chunks() if chunks is None else chunks
    return IndexGeneration.build(
        path,
        admitted,  # type: ignore[arg-type]
        snapshot_artifact_id="sha256:snapshot",
        model_lock_artifact_id="sha256:model-lock",
        limits=_limits(),
        hnsw_parameters=HnswParameters(m=2, ef_construction=8, ef_search=8, seed=7),
    )


def test_build_publishes_one_coherent_restartable_generation(tmp_path: Path) -> None:
    destination = tmp_path / "generation"

    with _build(destination) as generation:
        manifest = generation.manifest
        assert [receipt.stage for receipt in manifest.stages] == [
            "lexical",
            "dense_exact",
            "dense_hnsw",
        ]
        assert len({receipt.chunk_set_sha256 for receipt in manifest.stages}) == 1
        assert {receipt.item_count for receipt in manifest.stages} == {3}
        assert generation.lexical.query("ancient DNA", top_k=2)[0].chunk.chunk_id == (
            "chunk-a"
        )
        assert (
            generation.exact.query((1.0, 0.0, 0.0, 0.0), top_k=1)[0].chunk_id
            == "chunk-a"
        )
        assert (
            generation.hnsw.query((0.0, 1.0, 0.0, 0.0), top_k=1)[0].chunk_id
            == "chunk-b"
        )

    with IndexGeneration.open(destination) as restarted:
        assert restarted.manifest == manifest


def test_clean_rebuild_identity_is_independent_of_input_order(tmp_path: Path) -> None:
    with _build(tmp_path / "first") as first:
        first_manifest = first.manifest
    with _build(tmp_path / "second", reversed(_chunks())) as second:
        second_manifest = second.manifest

    assert second_manifest == first_manifest
    assert (tmp_path / "first" / "generation.json").read_bytes() == (
        tmp_path / "second" / "generation.json"
    ).read_bytes()


def test_lexical_segment_is_independent_and_dense_assembly_reuses_it(
    tmp_path: Path,
) -> None:
    lexical_path = tmp_path / "lexical.sqlite"
    receipt = build_lexical_index_segment(
        lexical_path,
        reversed(_lexical_chunks()),
        limits=_lexical_limits(),
    )

    assert receipt.stage == "lexical"
    assert receipt.file_name == "lexical.sqlite"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["lexical.sqlite"]

    with IndexGeneration.build_from_lexical(
        tmp_path / "assembled",
        lexical_path,
        _chunks(),
        snapshot_artifact_id="sha256:snapshot",
        model_lock_artifact_id="sha256:model-lock",
        limits=_limits(),
        hnsw_parameters=HnswParameters(m=2, ef_construction=8, ef_search=8, seed=7),
    ) as assembled:
        assembled_manifest = assembled.manifest
    with _build(tmp_path / "compatibility") as compatibility:
        compatibility_manifest = compatibility.manifest

    assert assembled_manifest == compatibility_manifest
    assert (
        lexical_path.read_bytes()
        == (tmp_path / "assembled" / "lexical.sqlite").read_bytes()
    )


def test_dense_assembly_rejects_a_lexical_segment_from_other_content(
    tmp_path: Path,
) -> None:
    lexical_path = tmp_path / "lexical.sqlite"
    changed = replace(_lexical_chunks()[0], text="substituted source text")
    build_lexical_index_segment(
        lexical_path,
        (changed, *_lexical_chunks()[1:]),
        limits=_lexical_limits(),
    )

    with pytest.raises(ValueError, match="does not match"):
        IndexGeneration.build_from_lexical(
            tmp_path / "generation",
            lexical_path,
            _chunks(),
            snapshot_artifact_id="sha256:snapshot",
            model_lock_artifact_id="sha256:model-lock",
            limits=_limits(),
        )

    assert lexical_path.is_file()
    assert not (tmp_path / "generation").exists()


@pytest.mark.parametrize(
    ("limits", "message"),
    [
        (replace(_limits(), max_chunks=2), "max_chunks"),
        (replace(_limits(), max_text_bytes=8), "max_text_bytes"),
        (replace(_limits(), max_vector_bytes=8), "max_vector_bytes"),
        (replace(_limits(), max_metadata_bytes=8), "max_metadata_bytes"),
    ],
)
def test_admission_limits_fail_before_publication(
    tmp_path: Path, limits: IndexBuildLimits, message: str
) -> None:
    destination = tmp_path / "generation"

    with pytest.raises(ValueError, match=message):
        IndexGeneration.build(
            destination,
            _chunks(),
            snapshot_artifact_id="sha256:snapshot",
            model_lock_artifact_id="sha256:model-lock",
            limits=limits,
        )

    assert not destination.exists()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("chunks", "message"),
    [
        ((_chunks()[0], _chunks()[0]), "unique"),
        ((_chunks()[0], replace(_chunks()[1], vector=(1.0, 2.0))), "dimension"),
        ((replace(_chunks()[0], text=""),), "ordinals and text"),
    ],
)
def test_invalid_admitted_chunks_are_rejected(
    tmp_path: Path, chunks: tuple[AdmittedIndexChunk, ...], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _build(tmp_path / "generation", chunks)


def test_backend_failure_reports_stage_and_removes_partial_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("injected dense failure")

    monkeypatch.setattr(FaissExactIndex, "build", fail)
    destination = tmp_path / "generation"

    with pytest.raises(IndexGenerationBuildError) as caught:
        _build(destination)

    assert caught.value.stage == "dense_exact"
    assert [receipt.stage for receipt in caught.value.completed_stages] == ["lexical"]
    assert not destination.exists()
    assert list(tmp_path.iterdir()) == []


def test_manifest_corruption_fails_closed(tmp_path: Path) -> None:
    destination = tmp_path / "generation"
    with _build(destination):
        pass
    manifest_path = destination / "generation.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["snapshot_artifact_id"] = "sha256:substituted"
    manifest_path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="identity"):
        IndexGeneration.open(destination)


def test_segment_corruption_fails_before_backend_open(tmp_path: Path) -> None:
    destination = tmp_path / "generation"
    with _build(destination):
        pass
    lexical_path = destination / "lexical.sqlite"
    with lexical_path.open("r+b") as handle:
        handle.seek(-1, 2)
        original = handle.read(1)
        handle.seek(-1, 2)
        handle.write(bytes([original[0] ^ 0xFF]))

    with pytest.raises(ValueError, match="segment hash mismatch"):
        IndexGeneration.open(destination)


def test_existing_destination_is_never_replaced(tmp_path: Path) -> None:
    destination = tmp_path / "generation"
    destination.mkdir()
    marker = destination / "owned"
    marker.write_text("preserve", encoding="utf-8")

    with pytest.raises(FileExistsError):
        _build(destination)

    assert marker.read_text(encoding="utf-8") == "preserve"
