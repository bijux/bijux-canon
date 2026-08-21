# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for atomic immutable generation activation."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("faiss")

from bijux_canon_index.application import (
    AdmittedIndexChunk,
    IndexActivationError,
    IndexBuildLimits,
    IndexGeneration,
    IndexGenerationRegistry,
)
from bijux_canon_index.infra.adapters.faiss.hnsw import HnswParameters


def _build(path: Path, identity: str) -> IndexGeneration:
    return IndexGeneration.build(
        path,
        (
            AdmittedIndexChunk(
                f"chunk-{identity}",
                f"document-{identity}",
                0,
                f"Ancient DNA evidence {identity}",
                (1.0, 0.0, 0.0),
                {"source_id": f"source-{identity}"},
            ),
        ),
        snapshot_artifact_id=f"sha256:snapshot-{identity}",
        model_lock_artifact_id="sha256:model",
        limits=IndexBuildLimits(10, 10_000, 10_000, 10_000),
        hnsw_parameters=HnswParameters(m=2, ef_construction=8, ef_search=8),
    )


def test_activation_retains_old_reader_and_generation(tmp_path: Path) -> None:
    registry = IndexGenerationRegistry(tmp_path / "registry")
    with _build(tmp_path / "first", "a") as first:
        first_id = registry.admit(first.path)
    with _build(tmp_path / "second", "b") as second:
        second_id = registry.admit(second.path)
    registry.activate(first_id)
    old_reader = registry.open_active()
    try:
        registry.activate(second_id)
        with registry.open_active() as current:
            assert current.manifest.generation_id == second_id
        assert old_reader.manifest.generation_id == first_id
        assert old_reader.lexical.query("ancient DNA")
    finally:
        old_reader.close()
    assert len(list(registry.generations.iterdir())) == 2


def test_partial_generation_is_never_admitted_or_activated(tmp_path: Path) -> None:
    registry = IndexGenerationRegistry(tmp_path / "registry")
    partial = tmp_path / "partial"
    partial.mkdir()
    (partial / "lexical.sqlite").write_bytes(b"partial")

    with pytest.raises(FileNotFoundError):
        registry.admit(partial)
    with pytest.raises((FileNotFoundError, IndexActivationError)):
        registry.activate("sha256:" + "0" * 64)
    assert registry.active_generation_id(required=False) is None


def test_recovery_removes_only_interrupted_publications(tmp_path: Path) -> None:
    registry = IndexGenerationRegistry(tmp_path / "registry")
    with _build(tmp_path / "first", "a") as first:
        generation_id = registry.admit(first.path)
    registry.activate(generation_id)
    interrupted_generation = registry.generations / ".deadbeef.building"
    interrupted_generation.mkdir()
    interrupted_pointer = registry.root / ".active.deadbeef.building"
    interrupted_pointer.write_text("partial", encoding="utf-8")
    unrelated = registry.root / "operator-note"
    unrelated.write_text("preserve", encoding="utf-8")

    removed = registry.recover()

    assert set(removed) == {interrupted_generation.name, interrupted_pointer.name}
    assert unrelated.read_text(encoding="utf-8") == "preserve"
    with registry.open_active() as active:
        assert active.manifest.generation_id == generation_id


def test_corrupt_active_pointer_fails_closed(tmp_path: Path) -> None:
    registry = IndexGenerationRegistry(tmp_path / "registry")
    (registry.root / "active.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(IndexActivationError, match="fields"):
        registry.open_active()


def test_failed_pointer_replacement_preserves_previous_activation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = IndexGenerationRegistry(tmp_path / "registry")
    with _build(tmp_path / "first", "a") as first:
        first_id = registry.admit(first.path)
    with _build(tmp_path / "second", "b") as second:
        second_id = registry.admit(second.path)
    registry.activate(first_id)

    def fail_replace(_source: os.PathLike[str], _target: os.PathLike[str]) -> None:
        raise OSError("injected pointer publication failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="publication failure"):
        registry.activate(second_id)

    assert registry.active_generation_id() == first_id
