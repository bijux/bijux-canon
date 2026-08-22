# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Content-addressed, corruption-detecting embedding persistence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import sqlite3
from typing import Any, Protocol

from bijux_canon_index.core.identity.ids import fingerprint
from bijux_canon_index.infra.runtime_paths import (
    default_embedding_cache_path,
    ensure_parent_dir,
)

_SCHEMA_VERSION = 2
_TABLE = "embeddings_cache"
_COLUMNS = {
    "key",
    "vector_json",
    "metadata_json",
    "dimension",
    "vector_sha256",
    "entry_sha256",
}


class EmbeddingCacheCorruptionError(RuntimeError):
    """A cache database or content-addressed entry failed verification."""


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _entry_digest(
    key: str,
    dimension: int,
    vector_sha256: str,
    metadata: dict[str, str | None],
) -> str:
    return _sha256(
        _canonical_json(
            {
                "dimension": dimension,
                "key": key,
                "metadata": metadata,
                "schema_version": _SCHEMA_VERSION,
                "vector_sha256": vector_sha256,
            }
        )
    )


@dataclass(frozen=True, slots=True)
class EmbeddingCacheEntry:
    """One finite vector and its canonical provenance metadata."""

    vector: tuple[float, ...]
    metadata: dict[str, str | None]

    def __post_init__(self) -> None:
        if not self.vector or any(not math.isfinite(value) for value in self.vector):
            raise ValueError("cached embedding vector must be non-empty and finite")
        if any(
            not isinstance(key, str) or not isinstance(value, str | None)
            for key, value in self.metadata.items()
        ):
            raise ValueError("cached embedding metadata must contain string values")
        object.__setattr__(self, "metadata", dict(self.metadata))


class EmbeddingCache(Protocol):
    """Persistence contract for verified embedding entries."""

    def get(self, key: str) -> EmbeddingCacheEntry | None:
        """Look up and verify a cached embedding entry."""

        ...

    def set(self, key: str, entry: EmbeddingCacheEntry) -> None:
        """Publish a verified embedding entry atomically."""

        ...


class SQLiteEmbeddingCache:
    """SQLite cache with canonical envelopes and atomic row publication."""

    def __init__(
        self,
        path: str | Path,
        *,
        expected_dimension: int | None = None,
    ) -> None:
        if expected_dimension is not None and expected_dimension < 1:
            raise ValueError("expected embedding dimension must be positive")
        self._path = ensure_parent_dir(path)
        self._expected_dimension = expected_dimension
        try:
            self._conn = sqlite3.connect(self._path)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=FULL")
            result = self._conn.execute("PRAGMA quick_check").fetchone()
            if result != ("ok",):
                raise EmbeddingCacheCorruptionError(
                    "embedding cache database is corrupt"
                )
            self._initialize_schema()
        except sqlite3.DatabaseError as error:
            raise EmbeddingCacheCorruptionError(
                "embedding cache database is unreadable"
            ) from error

    def _initialize_schema(self) -> None:
        existing = {
            str(row[1])
            for row in self._conn.execute(f"PRAGMA table_info({_TABLE})").fetchall()
        }
        with self._conn:
            if existing and existing != _COLUMNS:
                self._conn.execute(f"DROP TABLE {_TABLE}")
            self._conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {_TABLE}(
                    key TEXT PRIMARY KEY,
                    vector_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    dimension INTEGER NOT NULL CHECK(dimension > 0),
                    vector_sha256 TEXT NOT NULL,
                    entry_sha256 TEXT NOT NULL
                ) WITHOUT ROWID
                """
            )
            self._conn.execute(f"PRAGMA user_version={_SCHEMA_VERSION}")

    def close(self) -> None:
        """Close the cache connection after all committed writes are durable."""

        self._conn.close()

    def __enter__(self) -> SQLiteEmbeddingCache:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _require_dimension(self, dimension: int) -> None:
        if (
            self._expected_dimension is not None
            and dimension != self._expected_dimension
        ):
            raise EmbeddingCacheCorruptionError(
                "cached embedding dimension does not match the configured model"
            )

    def get(self, key: str) -> EmbeddingCacheEntry | None:
        """Return a verified entry or fail closed when its envelope is corrupt."""

        try:
            row = self._conn.execute(
                f"""
                SELECT vector_json, metadata_json, dimension,
                       vector_sha256, entry_sha256
                FROM {_TABLE} WHERE key=?
                """,
                (key,),
            ).fetchone()
        except sqlite3.DatabaseError as error:
            raise EmbeddingCacheCorruptionError(
                "embedding cache lookup failed integrity checks"
            ) from error
        if row is None:
            return None
        try:
            vector_json, metadata_json, dimension, vector_sha256, entry_sha256 = row
            vector_value = json.loads(vector_json)
            metadata_value = json.loads(metadata_json)
            if not isinstance(vector_value, list) or not isinstance(
                metadata_value, dict
            ):
                raise TypeError
            vector = tuple(float(value) for value in vector_value)
            metadata = {
                str(name): None if value is None else str(value)
                for name, value in metadata_value.items()
            }
            entry = EmbeddingCacheEntry(vector=vector, metadata=metadata)
            if (
                not isinstance(dimension, int)
                or dimension != len(entry.vector)
                or vector_json != _canonical_json(list(entry.vector))
                or metadata_json != _canonical_json(entry.metadata)
                or vector_sha256 != _sha256(vector_json)
                or entry_sha256
                != _entry_digest(key, dimension, vector_sha256, entry.metadata)
            ):
                raise ValueError
            self._require_dimension(dimension)
            return entry
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise EmbeddingCacheCorruptionError(
                f"cached embedding entry is corrupt: {key}"
            ) from error

    def set(self, key: str, entry: EmbeddingCacheEntry) -> None:
        """Publish one canonical entry in a fully committed SQLite transaction."""

        if not key:
            raise ValueError("embedding cache key must not be empty")
        dimension = len(entry.vector)
        self._require_dimension(dimension)
        vector_json = _canonical_json(list(entry.vector))
        metadata_json = _canonical_json(entry.metadata)
        vector_sha256 = _sha256(vector_json)
        entry_sha256 = _entry_digest(
            key,
            dimension,
            vector_sha256,
            entry.metadata,
        )
        try:
            with self._conn:
                self._conn.execute(
                    f"""
                    INSERT INTO {_TABLE}(
                        key, vector_json, metadata_json, dimension,
                        vector_sha256, entry_sha256
                    ) VALUES(?, ?, ?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        vector_json=excluded.vector_json,
                        metadata_json=excluded.metadata_json,
                        dimension=excluded.dimension,
                        vector_sha256=excluded.vector_sha256,
                        entry_sha256=excluded.entry_sha256
                    """,
                    (
                        key,
                        vector_json,
                        metadata_json,
                        dimension,
                        vector_sha256,
                        entry_sha256,
                    ),
                )
        except sqlite3.DatabaseError as error:
            raise EmbeddingCacheCorruptionError(
                "embedding cache publication failed atomically"
            ) from error


def build_cache(cache_spec: str | None) -> EmbeddingCache | None:
    """Build the configured embedding cache."""

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
    """Bind complete canonical text to its model and configuration identities."""

    if not model_id or not config_hash:
        raise ValueError(
            "embedding cache identity must include model and configuration"
        )
    digest = fingerprint(
        {
            "canonical_text": text,
            "config_identity": config_hash,
            "model_identity": model_id,
            "schema_version": "bijux.canon.index.embedding_cache_key.v1",
        }
    )
    return f"sha256:{digest}"


def embedding_config_hash(
    provider: str,
    model_id: str,
    options: Mapping[str, str] | None,
    *,
    provider_version: str | None = None,
) -> str:
    """Build the complete canonical provider configuration identity."""

    payload = {
        "provider": provider,
        "provider_version": provider_version,
        "model": model_id,
        "options": sorted((options or {}).items()),
    }
    return fingerprint(payload)


def metadata_as_dict(meta: Mapping[str, Any]) -> dict[str, str | None]:
    """Canonicalize arbitrary provider metadata for persistence."""

    return {
        str(key): None if value is None else str(value) for key, value in meta.items()
    }


__all__ = [
    "EmbeddingCache",
    "EmbeddingCacheCorruptionError",
    "EmbeddingCacheEntry",
    "SQLiteEmbeddingCache",
    "build_cache",
    "cache_key",
    "embedding_config_hash",
    "metadata_as_dict",
]
