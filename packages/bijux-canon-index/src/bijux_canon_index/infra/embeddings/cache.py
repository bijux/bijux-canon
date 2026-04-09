# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Cache helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any, Protocol

from bijux_canon_index.core.identity.ids import fingerprint
from bijux_canon_index.infra.runtime_paths import (
    default_embedding_cache_path,
    ensure_parent_dir,
)


@dataclass(frozen=True)
class EmbeddingCacheEntry:
    """Represents embedding cache entry."""

    vector: tuple[float, ...]
    metadata: dict[str, str | None]


class EmbeddingCache(Protocol):
    """Represents embedding cache."""

    def get(self, key: str) -> EmbeddingCacheEntry | None:
        """Look up a cached embedding entry."""

        ...

    def set(self, key: str, entry: EmbeddingCacheEntry) -> None:
        """Store a cached embedding entry."""

        ...


class SQLiteEmbeddingCache:
    """Represents SQLite embedding cache."""

    def __init__(self, path: str | Path) -> None:
        """Initialize the instance."""
        self._path = ensure_parent_dir(path)
        self._conn = sqlite3.connect(self._path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS embeddings_cache(key TEXT PRIMARY KEY, vector TEXT, metadata TEXT)"
        )
        self._conn.commit()

    def get(self, key: str) -> EmbeddingCacheEntry | None:
        """Handle get."""
        row = self._conn.execute(
            "SELECT vector, metadata FROM embeddings_cache WHERE key=?", (key,)
        ).fetchone()
        if not row:
            return None
        vector = tuple(float(v) for v in json.loads(row[0]))
        metadata = json.loads(row[1]) if row[1] else {}
        return EmbeddingCacheEntry(vector=vector, metadata=metadata)

    def set(self, key: str, entry: EmbeddingCacheEntry) -> None:
        """Handle set."""
        self._conn.execute(
            "REPLACE INTO embeddings_cache(key, vector, metadata) VALUES(?,?,?)",
            (key, json.dumps(list(entry.vector)), json.dumps(entry.metadata)),
        )
        self._conn.commit()


def build_cache(cache_spec: str | None) -> EmbeddingCache | None:
    """Build cache."""
    if not cache_spec:
        return None
    if cache_spec.lower() == "sqlite":
        return SQLiteEmbeddingCache(default_embedding_cache_path())
    if cache_spec.lower().startswith("sqlite:"):
        path = cache_spec.split(":", 1)[1]
        return SQLiteEmbeddingCache(path)
    if cache_spec.lower().startswith("vdb"):
        raise ValueError("VDB embedding cache is not supported yet")
    return SQLiteEmbeddingCache(cache_spec)


def cache_key(model_id: str, text: str, config_hash: str) -> str:
    """Handle cache key."""
    text_hash = fingerprint(text)
    return f"{model_id}:{text_hash}:{config_hash}"


def embedding_config_hash(
    provider: str,
    model_id: str,
    options: Mapping[str, str] | None,
    *,
    provider_version: str | None = None,
) -> str:
    """Handle embedding config hash."""
    payload = {
        "provider": provider,
        "provider_version": provider_version,
        "model": model_id,
        "options": sorted((options or {}).items()),
    }
    return fingerprint(payload)


def metadata_as_dict(meta: Mapping[str, Any]) -> dict[str, str | None]:
    """Handle metadata as dict."""
    return {str(k): None if v is None else str(v) for k, v in meta.items()}


__all__ = [
    "EmbeddingCacheEntry",
    "EmbeddingCache",
    "SQLiteEmbeddingCache",
    "build_cache",
    "cache_key",
    "metadata_as_dict",
    "embedding_config_hash",
]
