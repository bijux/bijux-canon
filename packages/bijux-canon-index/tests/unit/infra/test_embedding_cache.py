# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from bijux_canon_index.infra.embeddings.cache import (
    EmbeddingCacheEntry,
    SQLiteEmbeddingCache,
    build_cache,
)


def test_sqlite_embedding_cache_round_trip(tmp_path: Path) -> None:
    cache = SQLiteEmbeddingCache(tmp_path / "embeddings.sqlite")
    entry = EmbeddingCacheEntry(vector=(0.1, 0.2), metadata={"model": "mini"})

    cache.set("doc-1", entry)

    assert cache.get("doc-1") == entry


def test_build_cache_uses_workspace_default_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    cache = build_cache("sqlite")
    assert isinstance(cache, SQLiteEmbeddingCache)

    entry = EmbeddingCacheEntry(vector=(1.0,), metadata={"provider": "test"})
    cache.set("doc-2", entry)
    assert cache.get("doc-2") == entry
