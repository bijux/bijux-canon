# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any

from bijux_vex.core.identity.ids import fingerprint


@dataclass(frozen=True)
class EmbeddingCacheEntry:
    vector: tuple[float, ...]
    metadata: dict[str, str | None]


class EmbeddingCache:
    def get(self, key: str) -> EmbeddingCacheEntry | None:
        raise NotImplementedError

    def set(self, key: str, entry: EmbeddingCacheEntry) -> None:
        raise NotImplementedError


class SQLiteEmbeddingCache(EmbeddingCache):
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._conn = sqlite3.connect(self._path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS embeddings_cache(key TEXT PRIMARY KEY, vector TEXT, metadata TEXT)"
        )
        self._conn.commit()

    def get(self, key: str) -> EmbeddingCacheEntry | None:
        row = self._conn.execute(
            "SELECT vector, metadata FROM embeddings_cache WHERE key=?", (key,)
        ).fetchone()
        if not row:
            return None
        vector = tuple(float(v) for v in json.loads(row[0]))
        metadata = json.loads(row[1]) if row[1] else {}
        return EmbeddingCacheEntry(vector=vector, metadata=metadata)

    def set(self, key: str, entry: EmbeddingCacheEntry) -> None:
        self._conn.execute(
            "REPLACE INTO embeddings_cache(key, vector, metadata) VALUES(?,?,?)",
            (key, json.dumps(list(entry.vector)), json.dumps(entry.metadata)),
        )
        self._conn.commit()


def build_cache(cache_spec: str | None) -> EmbeddingCache | None:
    if not cache_spec:
        return None
    if cache_spec.lower() == "sqlite":
        return SQLiteEmbeddingCache(Path.cwd() / "embeddings-cache.sqlite")
    if cache_spec.lower().startswith("sqlite:"):
        path = cache_spec.split(":", 1)[1]
        return SQLiteEmbeddingCache(path)
    if cache_spec.lower().startswith("vdb"):
        raise ValueError("VDB embedding cache is not supported yet")
    return SQLiteEmbeddingCache(cache_spec)


def cache_key(model_id: str, text: str, config_hash: str) -> str:
    text_hash = fingerprint(text)
    return f"{model_id}:{text_hash}:{config_hash}"


def embedding_config_hash(
    provider: str,
    model_id: str,
    options: Mapping[str, str] | None,
    *,
    provider_version: str | None = None,
) -> str:
    payload = {
        "provider": provider,
        "provider_version": provider_version,
        "model": model_id,
        "options": sorted((options or {}).items()),
    }
    return fingerprint(payload)


def metadata_as_dict(meta: Mapping[str, Any]) -> dict[str, str | None]:
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
