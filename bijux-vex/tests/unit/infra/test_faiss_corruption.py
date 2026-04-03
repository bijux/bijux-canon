# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import json
from pathlib import Path

import pytest

from bijux_vex.core.errors import CorruptArtifactError

faiss = pytest.importorskip("faiss")

from bijux_vex.infra.adapters.faiss.adapter import FaissVectorStoreAdapter


def _make_adapter(path: Path) -> FaissVectorStoreAdapter:
    adapter = FaissVectorStoreAdapter(uri=str(path), options={"index_type": "exact"})
    adapter.connect()
    return adapter


def _seed_index(path: Path) -> None:
    adapter = _make_adapter(path)
    adapter.insert(
        [[0.0, 1.0, 2.0]],
        metadata=[{"vector_id": "vec-1", "chunk_id": "c1", "dimension": "3"}],
    )


def test_truncated_index_refuses_load(tmp_path: Path) -> None:
    index_path = tmp_path / "index.faiss"
    _seed_index(index_path)
    index_path.write_bytes(b"")
    adapter = FaissVectorStoreAdapter(
        uri=str(index_path), options={"index_type": "exact"}
    )
    with pytest.raises(CorruptArtifactError):
        adapter.connect()


def test_mismatched_metadata_refuses_load(tmp_path: Path) -> None:
    index_path = tmp_path / "index.faiss"
    _seed_index(index_path)
    meta_path = index_path.with_suffix(".meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["dimension"] = 128
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    adapter = FaissVectorStoreAdapter(
        uri=str(index_path), options={"index_type": "exact"}
    )
    with pytest.raises(CorruptArtifactError):
        adapter.connect()


def test_deleted_vectors_do_not_resurrect(tmp_path: Path) -> None:
    index_path = tmp_path / "index.faiss"
    adapter = _make_adapter(index_path)
    adapter.insert(
        [[0.0, 1.0, 2.0]],
        metadata=[{"vector_id": "vec-1", "chunk_id": "c1", "dimension": "3"}],
    )
    adapter.delete(["vec-1"])
    reloaded = _make_adapter(index_path)
    results = reloaded.query([0.0, 1.0, 2.0], 5, mode="deterministic")
    assert results == []
