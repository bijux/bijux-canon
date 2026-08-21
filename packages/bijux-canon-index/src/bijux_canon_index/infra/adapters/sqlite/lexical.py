# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Immutable SQLite FTS5 generations for deterministic lexical retrieval."""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
import sqlite3
import tempfile
from types import MappingProxyType
from typing import TypeAlias
import unicodedata

from bijux_canon_index.infra.runtime_paths import ensure_parent_dir

MetadataValue: TypeAlias = str | int | float | bool | None

SCHEMA_VERSION = 1
BACKEND_ID = "sqlite-fts5"
TOKENIZER = "unicode61 remove_diacritics 2"
TOKENIZER_IMPLEMENTATION = "sqlite-fts5-unicode61"


class LexicalIndexError(RuntimeError):
    """Base failure for persistent lexical index operations."""


class LexicalIndexCorruptionError(LexicalIndexError):
    """The database or one of its content-bound records failed verification."""


class LexicalIndexUnavailableError(LexicalIndexError):
    """The runtime cannot provide the required SQLite FTS5 capability."""


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


def _validated_metadata(
    metadata: Mapping[str, MetadataValue],
) -> Mapping[str, MetadataValue]:
    result: dict[str, MetadataValue] = {}
    for key, value in metadata.items():
        if not isinstance(key, str) or not key:
            raise ValueError("lexical metadata keys must be non-empty strings")
        if not isinstance(value, str | int | float | bool | None):
            raise ValueError("lexical metadata values must be JSON scalars")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("lexical metadata numbers must be finite")
        result[key] = value
    return MappingProxyType(dict(sorted(result.items())))


@dataclass(frozen=True, slots=True)
class LexicalChunk:
    """One admitted chunk and its exact filter metadata."""

    chunk_id: str
    document_id: str
    ordinal: int
    text: str
    metadata: Mapping[str, MetadataValue]

    def __post_init__(self) -> None:
        if not self.chunk_id or not self.document_id:
            raise ValueError("chunk and document identities must not be empty")
        if self.ordinal < 0:
            raise ValueError("chunk ordinal must not be negative")
        if not self.text:
            raise ValueError("lexical chunks must contain text")
        object.__setattr__(self, "metadata", _validated_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class LexicalSearchResult:
    """A deterministically ranked lexical match."""

    rank: int
    score: float
    chunk: LexicalChunk


@dataclass(frozen=True, slots=True)
class LexicalIndexManifest:
    """Content and runtime identities bound into one immutable generation."""

    generation_id: str
    chunk_count: int
    chunk_set_sha256: str
    content_root_sha256: str
    tokenizer: str
    tokenizer_configuration_sha256: str
    sqlite_version: str


def _chunk_payload(chunk: LexicalChunk) -> dict[str, object]:
    return {
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "metadata": dict(chunk.metadata),
        "ordinal": chunk.ordinal,
        "text": chunk.text,
    }


def _query_expression(query: str) -> str:
    normalized = " ".join(unicodedata.normalize("NFKC", query).casefold().split())
    if not normalized:
        raise ValueError("lexical query must not be empty")
    terms = []
    for term in sorted(normalized.split(" ")):
        escaped = term.replace('"', '""')
        terms.append(f'"{escaped}"')
    return " AND ".join(terms)


def _tokenizer_configuration_sha256() -> str:
    return _sha256(
        _canonical_json(
            {
                "implementation": TOKENIZER_IMPLEMENTATION,
                "query_normalization": "NFKC-casefold-whitespace-v1",
                "sqlite_tokenizer": TOKENIZER,
            }
        )
    )


def _generation_id(chunk_set_sha256: str, content_root_sha256: str) -> str:
    payload = {
        "backend": BACKEND_ID,
        "chunk_set_sha256": chunk_set_sha256,
        "content_root_sha256": content_root_sha256,
        "schema_version": SCHEMA_VERSION,
        "sqlite_version": sqlite3.sqlite_version,
        "tokenizer_configuration_sha256": _tokenizer_configuration_sha256(),
    }
    return f"sha256:{_sha256(_canonical_json(payload))}"


class SQLiteLexicalIndex:
    """Read-only API over an atomically published SQLite FTS5 generation."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path).resolve()
        if not self._path.is_file():
            raise FileNotFoundError(self._path)
        try:
            self._connection = sqlite3.connect(
                f"file:{self._path}?mode=rw",
                uri=True,
                timeout=5.0,
            )
            self._connection.execute("PRAGMA foreign_keys=ON")
            self._connection.execute("PRAGMA busy_timeout=5000")
            self._manifest = self._verify()
        except LexicalIndexError:
            connection = getattr(self, "_connection", None)
            if connection is not None:
                connection.close()
            raise
        except sqlite3.DatabaseError as error:
            connection = getattr(self, "_connection", None)
            if connection is not None:
                connection.close()
            raise LexicalIndexCorruptionError(
                "SQLite lexical generation is unreadable or corrupt"
            ) from error

    @classmethod
    def build(
        cls,
        path: str | Path,
        chunks: Iterable[LexicalChunk],
        *,
        replace: bool = False,
    ) -> SQLiteLexicalIndex:
        """Build and atomically publish a complete immutable generation."""

        destination = ensure_parent_dir(path)
        if destination.exists() and not replace:
            raise FileExistsError(destination)
        admitted = sorted(chunks, key=lambda chunk: chunk.chunk_id)
        if not admitted:
            raise ValueError("a lexical generation requires at least one chunk")
        chunk_ids = [chunk.chunk_id for chunk in admitted]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("chunk identities must be unique within a generation")

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".building",
            dir=destination.parent,
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            cls._write_generation(temporary, admitted)
            with temporary.open("rb") as handle:
                os.fsync(handle.fileno())
            if replace:
                os.replace(temporary, destination)
            else:
                os.link(temporary, destination)
                temporary.unlink()
            directory_descriptor = os.open(destination.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        return cls(destination)

    @classmethod
    def _write_generation(
        cls,
        path: Path,
        chunks: Sequence[LexicalChunk],
    ) -> None:
        connection = sqlite3.connect(path)
        try:
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            connection.execute("BEGIN IMMEDIATE")
            connection.executescript(
                f"""
                CREATE TABLE lexical_chunks(
                    row_id INTEGER PRIMARY KEY,
                    chunk_id TEXT NOT NULL UNIQUE,
                    document_id TEXT NOT NULL,
                    ordinal INTEGER NOT NULL CHECK(ordinal >= 0),
                    text TEXT NOT NULL CHECK(length(text) > 0),
                    metadata_json TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL
                );
                CREATE TABLE lexical_chunk_metadata(
                    chunk_id TEXT NOT NULL REFERENCES lexical_chunks(chunk_id),
                    key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    PRIMARY KEY(chunk_id, key)
                ) WITHOUT ROWID;
                CREATE INDEX lexical_chunk_metadata_filter
                    ON lexical_chunk_metadata(key, value_json, chunk_id);
                CREATE TABLE lexical_generation(
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                ) WITHOUT ROWID;
                CREATE VIRTUAL TABLE lexical_search USING fts5(
                    text,
                    content='lexical_chunks',
                    content_rowid='row_id',
                    tokenize='{TOKENIZER}'
                );
                """
            )
            content_digests: list[str] = []
            for row_id, chunk in enumerate(chunks, start=1):
                payload = _chunk_payload(chunk)
                metadata_json = _canonical_json(payload["metadata"])
                content_sha256 = _sha256(_canonical_json(payload))
                content_digests.append(content_sha256)
                connection.execute(
                    """
                    INSERT INTO lexical_chunks(
                        row_id, chunk_id, document_id, ordinal, text,
                        metadata_json, content_sha256
                    ) VALUES(?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row_id,
                        chunk.chunk_id,
                        chunk.document_id,
                        chunk.ordinal,
                        chunk.text,
                        metadata_json,
                        content_sha256,
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO lexical_chunk_metadata(chunk_id, key, value_json)
                    VALUES(?, ?, ?)
                    """,
                    [
                        (chunk.chunk_id, key, _canonical_json(value))
                        for key, value in chunk.metadata.items()
                    ],
                )
            connection.execute(
                "INSERT INTO lexical_search(lexical_search) VALUES('rebuild')"
            )

            chunk_set_sha256 = _sha256(
                _canonical_json([chunk.chunk_id for chunk in chunks])
            )
            content_root_sha256 = _sha256(_canonical_json(content_digests))
            tokenizer_hash = _tokenizer_configuration_sha256()
            generation_id = _generation_id(chunk_set_sha256, content_root_sha256)
            settings = {
                "backend": BACKEND_ID,
                "chunk_count": str(len(chunks)),
                "chunk_set_sha256": chunk_set_sha256,
                "content_root_sha256": content_root_sha256,
                "generation_id": generation_id,
                "sqlite_version": sqlite3.sqlite_version,
                "tokenizer": TOKENIZER,
                "tokenizer_configuration_sha256": tokenizer_hash,
            }
            connection.executemany(
                "INSERT INTO lexical_generation(key, value) VALUES(?, ?)",
                sorted(settings.items()),
            )
            connection.commit()
            connection.execute(
                "INSERT INTO lexical_search(lexical_search, rank) VALUES('integrity-check', 1)"
            )
        except sqlite3.OperationalError as error:
            connection.rollback()
            if "fts5" in str(error).lower() or "no such module" in str(error).lower():
                raise LexicalIndexUnavailableError(
                    "the SQLite runtime does not provide required FTS5 support"
                ) from error
            raise
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @property
    def manifest(self) -> LexicalIndexManifest:
        """Return the verified immutable generation identity."""

        return self._manifest

    def close(self) -> None:
        """Close the generation connection."""

        self._connection.close()

    def __enter__(self) -> SQLiteLexicalIndex:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _settings(self) -> dict[str, str]:
        return {
            str(key): str(value)
            for key, value in self._connection.execute(
                "SELECT key, value FROM lexical_generation ORDER BY key"
            )
        }

    def _verify(self) -> LexicalIndexManifest:
        if self._connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise LexicalIndexCorruptionError(
                "SQLite lexical generation failed database integrity checks"
            )
        if self._connection.execute("PRAGMA user_version").fetchone() != (
            SCHEMA_VERSION,
        ):
            raise LexicalIndexCorruptionError(
                "SQLite lexical generation schema version is unsupported"
            )
        settings = self._settings()
        expected_keys = {
            "backend",
            "chunk_count",
            "chunk_set_sha256",
            "content_root_sha256",
            "generation_id",
            "sqlite_version",
            "tokenizer",
            "tokenizer_configuration_sha256",
        }
        if set(settings) != expected_keys:
            raise LexicalIndexCorruptionError(
                "SQLite lexical generation metadata is incomplete"
            )
        if (
            settings["backend"] != BACKEND_ID
            or settings["sqlite_version"] != sqlite3.sqlite_version
            or settings["tokenizer"] != TOKENIZER
            or settings["tokenizer_configuration_sha256"]
            != _tokenizer_configuration_sha256()
        ):
            raise LexicalIndexCorruptionError(
                "SQLite lexical generation backend or tokenizer identity drifted"
            )

        rows = self._connection.execute(
            """
            SELECT chunk_id, document_id, ordinal, text,
                   metadata_json, content_sha256
            FROM lexical_chunks ORDER BY chunk_id
            """
        ).fetchall()
        chunk_ids: list[str] = []
        content_digests: list[str] = []
        expected_metadata_rows: list[tuple[str, str, str]] = []
        try:
            for (
                chunk_id,
                document_id,
                ordinal,
                text,
                metadata_json,
                stored_digest,
            ) in rows:
                metadata_value = json.loads(metadata_json)
                if not isinstance(metadata_value, dict):
                    raise TypeError
                chunk = LexicalChunk(
                    chunk_id=str(chunk_id),
                    document_id=str(document_id),
                    ordinal=int(ordinal),
                    text=str(text),
                    metadata=metadata_value,
                )
                if metadata_json != _canonical_json(dict(chunk.metadata)):
                    raise ValueError
                digest = _sha256(_canonical_json(_chunk_payload(chunk)))
                if stored_digest != digest:
                    raise ValueError
                chunk_ids.append(chunk.chunk_id)
                content_digests.append(digest)
                expected_metadata_rows.extend(
                    (chunk.chunk_id, key, _canonical_json(value))
                    for key, value in chunk.metadata.items()
                )
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            raise LexicalIndexCorruptionError(
                "SQLite lexical chunk content failed hash verification"
            ) from error

        metadata_rows = self._connection.execute(
            """
            SELECT chunk_id, key, value_json
            FROM lexical_chunk_metadata ORDER BY chunk_id, key
            """
        ).fetchall()
        if metadata_rows != expected_metadata_rows:
            raise LexicalIndexCorruptionError(
                "SQLite lexical filter metadata does not match chunk content"
            )
        chunk_set_sha256 = _sha256(_canonical_json(chunk_ids))
        content_root_sha256 = _sha256(_canonical_json(content_digests))
        try:
            declared_count = int(settings["chunk_count"])
        except ValueError as error:
            raise LexicalIndexCorruptionError(
                "SQLite lexical generation chunk count is invalid"
            ) from error
        if (
            declared_count != len(rows)
            or settings["chunk_set_sha256"] != chunk_set_sha256
            or settings["content_root_sha256"] != content_root_sha256
            or self._connection.execute(
                "SELECT count(*) FROM lexical_search"
            ).fetchone()
            != (len(rows),)
        ):
            raise LexicalIndexCorruptionError(
                "SQLite lexical generation identity does not match stored chunks"
            )
        try:
            self._connection.execute(
                "INSERT INTO lexical_search(lexical_search, rank) VALUES('integrity-check', 1)"
            )
        except sqlite3.DatabaseError as error:
            raise LexicalIndexCorruptionError(
                "SQLite FTS5 index failed integrity verification"
            ) from error

        expected_generation_id = _generation_id(
            chunk_set_sha256,
            content_root_sha256,
        )
        if settings["generation_id"] != expected_generation_id:
            raise LexicalIndexCorruptionError(
                "SQLite lexical generation identifier failed verification"
            )
        return LexicalIndexManifest(
            generation_id=expected_generation_id,
            chunk_count=len(rows),
            chunk_set_sha256=chunk_set_sha256,
            content_root_sha256=content_root_sha256,
            tokenizer=TOKENIZER,
            tokenizer_configuration_sha256=_tokenizer_configuration_sha256(),
            sqlite_version=sqlite3.sqlite_version,
        )

    def query(
        self,
        query: str,
        *,
        top_k: int = 10,
        filters: Mapping[str, MetadataValue] | None = None,
        document_ids: Sequence[str] | None = None,
    ) -> tuple[LexicalSearchResult, ...]:
        """Run a parameterized BM25 query with deterministic tie breaking."""

        if not 1 <= top_k <= 1000:
            raise ValueError("top_k must be between 1 and 1000")
        normalized_filters = _validated_metadata(filters or {})
        if document_ids is not None and not document_ids:
            return ()

        clauses = ["lexical_search MATCH ?"]
        parameters: list[object] = [_query_expression(query)]
        for index, (key, value) in enumerate(normalized_filters.items()):
            alias = f"filter_{index}"
            clauses.append(
                f"EXISTS (SELECT 1 FROM lexical_chunk_metadata {alias} "
                f"WHERE {alias}.chunk_id = chunks.chunk_id "
                f"AND {alias}.key = ? AND {alias}.value_json = ?)"
            )
            parameters.extend((key, _canonical_json(value)))
        if document_ids is not None:
            if len(document_ids) > 1000:
                raise ValueError("document filters must not exceed 1000 identities")
            if any(not isinstance(value, str) or not value for value in document_ids):
                raise ValueError("document filters must contain non-empty identities")
            normalized_document_ids = sorted(set(document_ids))
            placeholders = ",".join("?" for _ in normalized_document_ids)
            clauses.append(f"chunks.document_id IN ({placeholders})")
            parameters.extend(normalized_document_ids)
        parameters.append(top_k)
        rows = self._connection.execute(
            f"""
            SELECT chunks.chunk_id, chunks.document_id, chunks.ordinal,
                   chunks.text, chunks.metadata_json, bm25(lexical_search)
            FROM lexical_search
            JOIN lexical_chunks chunks
              ON chunks.row_id = lexical_search.rowid
            WHERE {" AND ".join(clauses)}
            ORDER BY bm25(lexical_search) ASC, chunks.chunk_id ASC
            LIMIT ?
            """,
            parameters,
        ).fetchall()
        results = []
        for rank, row in enumerate(rows, start=1):
            chunk_id, document_id, ordinal, text, metadata_json, score = row
            chunk = LexicalChunk(
                chunk_id=str(chunk_id),
                document_id=str(document_id),
                ordinal=int(ordinal),
                text=str(text),
                metadata=json.loads(metadata_json),
            )
            results.append(
                LexicalSearchResult(rank=rank, score=-float(score), chunk=chunk)
            )
        return tuple(results)


__all__ = [
    "BACKEND_ID",
    "SCHEMA_VERSION",
    "TOKENIZER",
    "LexicalChunk",
    "LexicalIndexCorruptionError",
    "LexicalIndexError",
    "LexicalIndexManifest",
    "LexicalIndexUnavailableError",
    "LexicalSearchResult",
    "MetadataValue",
    "SQLiteLexicalIndex",
]
