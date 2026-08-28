# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from bijux_canon_index.infra.embeddings.cache import (
    EmbeddingCacheCorruptionError,
    EmbeddingCacheEntry,
    SQLiteEmbeddingCache,
    build_cache,
    cache_key,
)


def test_sqlite_embedding_cache_survives_restart(tmp_path: Path) -> None:
    path = tmp_path / "embeddings.sqlite"
    entry = EmbeddingCacheEntry(
        vector=(0.6, 0.8),
        metadata={"model_lock_id": "sha256:model"},
    )
    key = cache_key("sha256:model", "complete canonical text", "sha256:config")

    with SQLiteEmbeddingCache(path, expected_dimension=2) as cache:
        cache.set(key, entry)
    with SQLiteEmbeddingCache(path, expected_dimension=2) as reopened:
        assert reopened.get(key) == entry


def test_cache_key_binds_text_model_and_configuration() -> None:
    baseline = cache_key("model-a", "alpha:beta", "config-a")

    assert baseline.startswith("sha256:")
    assert len(baseline) == 71
    assert cache_key("model-a", "alpha:beta", "config-a") == baseline
    assert cache_key("model-b", "alpha:beta", "config-a") != baseline
    assert cache_key("model-a", "alpha", "beta:config-a") != baseline
    assert cache_key("model-a", "alpha:beta", "config-b") != baseline


def test_sqlite_embedding_cache_detects_content_corruption(tmp_path: Path) -> None:
    path = tmp_path / "embeddings.sqlite"
    key = cache_key("model", "text", "config")
    with SQLiteEmbeddingCache(path, expected_dimension=2) as cache:
        cache.set(key, EmbeddingCacheEntry((0.6, 0.8), {"source": "real"}))
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE embeddings_cache SET vector_json=? WHERE key=?",
            ("[0.8,0.6]", key),
        )

    with (
        SQLiteEmbeddingCache(path, expected_dimension=2) as cache,
        pytest.raises(EmbeddingCacheCorruptionError, match="entry is corrupt"),
    ):
        cache.get(key)


def test_sqlite_embedding_cache_rolls_back_failed_publication(
    tmp_path: Path,
) -> None:
    path = tmp_path / "embeddings.sqlite"
    key = cache_key("model", "text", "config")
    original = EmbeddingCacheEntry((0.6, 0.8), {"generation": "original"})
    replacement = EmbeddingCacheEntry((0.8, 0.6), {"generation": "replacement"})
    with SQLiteEmbeddingCache(path, expected_dimension=2) as cache:
        cache.set(key, original)
        with sqlite3.connect(path) as connection:
            connection.execute(
                """
                CREATE TRIGGER reject_cache_update
                BEFORE UPDATE ON embeddings_cache
                BEGIN
                    SELECT RAISE(ABORT, 'injected publication failure');
                END
                """
            )
        with pytest.raises(EmbeddingCacheCorruptionError, match="atomically"):
            cache.set(key, replacement)
        with sqlite3.connect(path) as connection:
            connection.execute("DROP TRIGGER reject_cache_update")
        assert cache.get(key) == original


def test_sqlite_embedding_cache_enforces_model_dimension(tmp_path: Path) -> None:
    cache = SQLiteEmbeddingCache(tmp_path / "embeddings.sqlite", expected_dimension=384)
    with cache, pytest.raises(EmbeddingCacheCorruptionError, match="dimension"):
        cache.set("key", EmbeddingCacheEntry((1.0, 0.0), {}))


@pytest.mark.parametrize("dimension", [16, 384])
def test_sqlite_embedding_cache_supports_declared_profile_dimensions(
    tmp_path: Path,
    dimension: int,
) -> None:
    vector = (1.0,) + (0.0,) * (dimension - 1)
    entry = EmbeddingCacheEntry(vector, {"profile_dimension": str(dimension)})
    with SQLiteEmbeddingCache(
        tmp_path / f"embeddings-{dimension}.sqlite",
        expected_dimension=dimension,
    ) as cache:
        cache.set("key", entry)
        assert cache.get("key") == entry


def test_sqlite_embedding_cache_invalidates_legacy_schema(tmp_path: Path) -> None:
    path = tmp_path / "embeddings.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE embeddings_cache(key TEXT PRIMARY KEY, vector TEXT, metadata TEXT)"
        )
        connection.execute(
            "INSERT INTO embeddings_cache VALUES('legacy', '[1.0]', '{}')"
        )

    with SQLiteEmbeddingCache(path) as cache:
        assert cache.get("legacy") is None


def test_embedding_cache_rejects_nonfinite_vectors() -> None:
    with pytest.raises(ValueError, match="finite"):
        EmbeddingCacheEntry((float("nan"),), {})


def test_build_cache_uses_workspace_default_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    cache = build_cache("sqlite")
    assert isinstance(cache, SQLiteEmbeddingCache)
    assert cache is not None
    with cache:
        entry = EmbeddingCacheEntry(vector=(1.0,), metadata={"provider": "test"})
        cache.set("doc-2", entry)
        assert cache.get("doc-2") == entry
