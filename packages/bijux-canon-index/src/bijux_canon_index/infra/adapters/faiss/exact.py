# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Immutable, content-verified FAISS IndexFlatIP generations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Any

from bijux_canon_index.domain.metadata_filters import (
    MetadataFilter,
    MetadataValue,
    matches_metadata_filter,
    validated_metadata,
)
from bijux_canon_index.infra.runtime_paths import ensure_parent_dir

faiss: Any
np: Any
try:  # pragma: no cover - availability is exercised by installed-profile checks
    import faiss as _faiss  # type: ignore[import-not-found, import-untyped, unused-ignore]
    import numpy as _np
except Exception:  # pragma: no cover - optional dependency
    faiss = None
    np = None
else:
    faiss = _faiss
    np = _np

_validated_metadata = validated_metadata

SCHEMA_VERSION = 1
BACKEND_ID = "faiss-flat-ip"
INDEX_TYPE = "IndexFlatIP"
METRIC = "inner_product"
NORMALIZATION = "l2-float32-v1"


class FaissExactIndexError(RuntimeError):
    """Base failure for exact dense generation operations."""


class FaissExactIndexCorruptionError(FaissExactIndexError):
    """A stored exact dense generation failed content verification."""


class FaissExactIndexUnavailableError(FaissExactIndexError):
    """The required FAISS and NumPy runtime is unavailable."""


def _require_runtime() -> tuple[Any, Any]:
    if faiss is None or np is None:
        raise FaissExactIndexUnavailableError(
            "FAISS exact storage requires the bijux-canon-index vdb dependencies"
        )
    return faiss, np


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: object) -> str:
    return _sha256_bytes(_canonical_json(value).encode("utf-8"))


def _validated_vector(vector: Sequence[float]) -> tuple[float, ...]:
    result = tuple(float(value) for value in vector)
    if not result:
        raise ValueError("dense vectors must not be empty")
    if any(not math.isfinite(value) for value in result):
        raise ValueError("dense vectors must contain only finite values")
    return result


@dataclass(frozen=True, slots=True)
class DenseVectorRecord:
    """One admitted chunk, vector, and exact filter metadata."""

    chunk_id: str
    vector: Sequence[float]
    metadata: Mapping[str, MetadataValue]

    def __post_init__(self) -> None:
        if not self.chunk_id:
            raise ValueError("dense chunk identity must not be empty")
        object.__setattr__(self, "vector", _validated_vector(self.vector))
        object.__setattr__(self, "metadata", _validated_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class _StoredRecord:
    position: int
    chunk_id: str
    metadata: Mapping[str, MetadataValue]
    vector_sha256: str


@dataclass(frozen=True, slots=True)
class FaissExactSearchResult:
    """One exactly scored result with stable chunk mapping."""

    rank: int
    score: float
    chunk_id: str
    metadata: Mapping[str, MetadataValue]


@dataclass(frozen=True, slots=True)
class FaissExactIndexManifest:
    """Complete content and runtime identity for an exact dense generation."""

    generation_id: str
    model_lock_artifact_id: str
    vector_count: int
    dimension: int
    chunk_set_sha256: str
    record_root_sha256: str
    index_sha256: str
    faiss_version: str
    numpy_version: str
    index_type: str = INDEX_TYPE
    metric: str = METRIC
    normalization: str = NORMALIZATION


def _normalize_vector(vector: Sequence[float], *, dimension: int | None = None) -> Any:
    _, numpy = _require_runtime()
    validated = _validated_vector(vector)
    if dimension is not None and len(validated) != dimension:
        raise ValueError(
            f"dense vector dimension {len(validated)} does not match {dimension}"
        )
    array = numpy.asarray(validated, dtype="float32")
    norm = float(numpy.linalg.norm(array.astype("float64")))
    if not math.isfinite(norm) or norm == 0.0:
        raise ValueError("dense vectors must have a finite non-zero norm")
    normalized = numpy.asarray(array.astype("float64") / norm, dtype="float32")
    return numpy.ascontiguousarray(normalized)


def _vector_sha256(vector: Any) -> str:
    _, numpy = _require_runtime()
    canonical = numpy.asarray(vector, dtype="<f4")
    return _sha256_bytes(canonical.tobytes(order="C"))


def normalized_vector_sha256(
    vector: Sequence[float], *, dimension: int | None = None
) -> str:
    """Return the exact backend's canonical normalized query-vector identity."""

    return _vector_sha256(_normalize_vector(vector, dimension=dimension))


def _generation_id(settings: Mapping[str, str]) -> str:
    identity = {key: value for key, value in settings.items() if key != "generation_id"}
    return f"sha256:{_sha256_json(identity)}"


class FaissExactIndex:
    """Read-only API over one atomically published IndexFlatIP generation."""

    def __init__(self, path: str | Path) -> None:
        _require_runtime()
        self._path = Path(path).resolve()
        if not self._path.is_file():
            raise FileNotFoundError(self._path)
        try:
            self._connection = sqlite3.connect(
                f"file:{self._path}?mode=rw",
                uri=True,
                timeout=5.0,
            )
            self._connection.execute("PRAGMA busy_timeout=5000")
            self._manifest, self._index, self._records = self._verify()
        except FaissExactIndexError:
            connection = getattr(self, "_connection", None)
            if connection is not None:
                connection.close()
            raise
        except sqlite3.DatabaseError as error:
            connection = getattr(self, "_connection", None)
            if connection is not None:
                connection.close()
            raise FaissExactIndexCorruptionError(
                "FAISS exact generation container is unreadable or corrupt"
            ) from error

    @classmethod
    def build(
        cls,
        path: str | Path,
        records: Iterable[DenseVectorRecord],
        *,
        model_lock_artifact_id: str,
        replace: bool = False,
    ) -> FaissExactIndex:
        """Build and atomically publish a complete exact dense generation."""

        _require_runtime()
        if not model_lock_artifact_id:
            raise ValueError("a dense generation requires a model lock identity")
        destination = ensure_parent_dir(path)
        if destination.exists() and not replace:
            raise FileExistsError(destination)
        admitted = sorted(records, key=lambda record: record.chunk_id)
        if not admitted:
            raise ValueError("an exact dense generation requires at least one vector")
        chunk_ids = [record.chunk_id for record in admitted]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("chunk identities must be unique within a generation")
        dimension = len(admitted[0].vector)
        if any(len(record.vector) != dimension for record in admitted):
            raise ValueError("all dense vectors must have the same dimension")

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".building",
            dir=destination.parent,
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            cls._write_generation(
                temporary,
                admitted,
                model_lock_artifact_id=model_lock_artifact_id,
            )
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
        records: Sequence[DenseVectorRecord],
        *,
        model_lock_artifact_id: str,
    ) -> None:
        faiss_runtime, numpy = _require_runtime()
        dimension = len(records[0].vector)
        vectors = numpy.stack(
            [
                _normalize_vector(record.vector, dimension=dimension)
                for record in records
            ]
        ).astype("float32", copy=False)
        index = faiss_runtime.IndexFlatIP(dimension)
        index.add(vectors)
        index_bytes = bytes(faiss_runtime.serialize_index(index))
        index_sha256 = _sha256_bytes(index_bytes)

        stored_records = []
        record_identities = []
        for position, (record, vector) in enumerate(zip(records, vectors, strict=True)):
            metadata_json = _canonical_json(dict(record.metadata))
            vector_sha256 = _vector_sha256(vector)
            stored_records.append(
                (position, record.chunk_id, metadata_json, vector_sha256)
            )
            record_identities.append(
                {
                    "chunk_id": record.chunk_id,
                    "metadata": dict(record.metadata),
                    "position": position,
                    "vector_sha256": vector_sha256,
                }
            )
        faiss_version = str(getattr(faiss_runtime, "__version__", "unknown"))
        numpy_version = str(numpy.__version__)
        settings = {
            "backend": BACKEND_ID,
            "chunk_set_sha256": _sha256_json([record.chunk_id for record in records]),
            "dimension": str(dimension),
            "faiss_version": faiss_version,
            "index_sha256": index_sha256,
            "index_type": INDEX_TYPE,
            "metric": METRIC,
            "model_lock_artifact_id": model_lock_artifact_id,
            "normalization": NORMALIZATION,
            "numpy_version": numpy_version,
            "record_root_sha256": _sha256_json(record_identities),
            "vector_count": str(len(records)),
        }
        settings["generation_id"] = _generation_id(settings)

        connection = sqlite3.connect(path)
        try:
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            connection.executescript(
                """
                CREATE TABLE dense_generation(
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                ) WITHOUT ROWID;
                CREATE TABLE dense_index(
                    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
                    serialized_index BLOB NOT NULL,
                    index_sha256 TEXT NOT NULL
                );
                CREATE TABLE dense_records(
                    position INTEGER PRIMARY KEY CHECK(position >= 0),
                    chunk_id TEXT NOT NULL UNIQUE,
                    metadata_json TEXT NOT NULL,
                    vector_sha256 TEXT NOT NULL
                );
                """
            )
            with connection:
                connection.executemany(
                    "INSERT INTO dense_generation(key, value) VALUES(?, ?)",
                    sorted(settings.items()),
                )
                connection.execute(
                    """
                    INSERT INTO dense_index(
                        singleton, serialized_index, index_sha256
                    ) VALUES(1, ?, ?)
                    """,
                    (index_bytes, index_sha256),
                )
                connection.executemany(
                    """
                    INSERT INTO dense_records(
                        position, chunk_id, metadata_json, vector_sha256
                    ) VALUES(?, ?, ?, ?)
                    """,
                    stored_records,
                )
        finally:
            connection.close()

    @property
    def manifest(self) -> FaissExactIndexManifest:
        """Return the verified immutable generation identity."""

        return self._manifest

    def close(self) -> None:
        """Close the generation container."""

        self._connection.close()

    def __enter__(self) -> FaissExactIndex:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _settings(self) -> dict[str, str]:
        return {
            str(key): str(value)
            for key, value in self._connection.execute(
                "SELECT key, value FROM dense_generation ORDER BY key"
            )
        }

    def _verify(self) -> tuple[FaissExactIndexManifest, Any, tuple[_StoredRecord, ...]]:
        faiss_runtime, numpy = _require_runtime()
        if self._connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise FaissExactIndexCorruptionError(
                "FAISS exact generation failed database integrity checks"
            )
        if self._connection.execute("PRAGMA user_version").fetchone() != (
            SCHEMA_VERSION,
        ):
            raise FaissExactIndexCorruptionError(
                "FAISS exact generation schema version is unsupported"
            )
        settings = self._settings()
        expected_keys = {
            "backend",
            "chunk_set_sha256",
            "dimension",
            "faiss_version",
            "generation_id",
            "index_sha256",
            "index_type",
            "metric",
            "model_lock_artifact_id",
            "normalization",
            "numpy_version",
            "record_root_sha256",
            "vector_count",
        }
        if set(settings) != expected_keys:
            raise FaissExactIndexCorruptionError(
                "FAISS exact generation metadata is incomplete"
            )
        if (
            settings["backend"] != BACKEND_ID
            or settings["index_type"] != INDEX_TYPE
            or settings["metric"] != METRIC
            or settings["normalization"] != NORMALIZATION
            or settings["faiss_version"]
            != str(getattr(faiss_runtime, "__version__", "unknown"))
            or settings["numpy_version"] != str(numpy.__version__)
        ):
            raise FaissExactIndexCorruptionError(
                "FAISS exact generation backend identity drifted"
            )
        try:
            dimension = int(settings["dimension"])
            vector_count = int(settings["vector_count"])
        except ValueError as error:
            raise FaissExactIndexCorruptionError(
                "FAISS exact generation dimensions are invalid"
            ) from error
        if dimension < 1 or vector_count < 1:
            raise FaissExactIndexCorruptionError(
                "FAISS exact generation dimensions are invalid"
            )

        index_row = self._connection.execute(
            "SELECT serialized_index, index_sha256 FROM dense_index WHERE singleton=1"
        ).fetchone()
        if index_row is None:
            raise FaissExactIndexCorruptionError(
                "FAISS exact generation is missing its serialized index"
            )
        index_bytes, stored_index_sha256 = index_row
        if (
            not isinstance(index_bytes, bytes)
            or stored_index_sha256 != _sha256_bytes(index_bytes)
            or settings["index_sha256"] != stored_index_sha256
        ):
            raise FaissExactIndexCorruptionError(
                "FAISS exact serialized index checksum failed"
            )
        try:
            index = faiss_runtime.deserialize_index(
                numpy.frombuffer(index_bytes, dtype="uint8")
            )
        except Exception as error:
            raise FaissExactIndexCorruptionError(
                "FAISS exact serialized index failed to load"
            ) from error
        if (
            type(index).__name__ != INDEX_TYPE
            or int(index.d) != dimension
            or int(index.ntotal) != vector_count
            or int(index.metric_type) != int(faiss_runtime.METRIC_INNER_PRODUCT)
        ):
            raise FaissExactIndexCorruptionError(
                "FAISS exact serialized index parameters do not match its manifest"
            )

        rows = self._connection.execute(
            """
            SELECT position, chunk_id, metadata_json, vector_sha256
            FROM dense_records ORDER BY position
            """
        ).fetchall()
        if len(rows) != vector_count:
            raise FaissExactIndexCorruptionError(
                "FAISS exact chunk mapping count does not match the index"
            )
        stored_records = []
        record_identities = []
        chunk_ids = []
        try:
            for expected_position, row in enumerate(rows):
                position, chunk_id, metadata_json, vector_sha256 = row
                metadata_value = json.loads(metadata_json)
                if position != expected_position or not isinstance(
                    metadata_value, dict
                ):
                    raise ValueError
                metadata = _validated_metadata(metadata_value)
                if metadata_json != _canonical_json(dict(metadata)):
                    raise ValueError
                vector = index.reconstruct(expected_position)
                if vector_sha256 != _vector_sha256(vector):
                    raise ValueError
                norm = float(numpy.linalg.norm(vector.astype("float64")))
                if not math.isclose(norm, 1.0, rel_tol=1e-6, abs_tol=1e-6):
                    raise ValueError
                record = _StoredRecord(
                    position=expected_position,
                    chunk_id=str(chunk_id),
                    metadata=metadata,
                    vector_sha256=str(vector_sha256),
                )
                stored_records.append(record)
                chunk_ids.append(record.chunk_id)
                record_identities.append(
                    {
                        "chunk_id": record.chunk_id,
                        "metadata": dict(record.metadata),
                        "position": record.position,
                        "vector_sha256": record.vector_sha256,
                    }
                )
        except (json.JSONDecodeError, TypeError, ValueError, RuntimeError) as error:
            raise FaissExactIndexCorruptionError(
                "FAISS exact chunk mapping or vector checksum failed"
            ) from error
        if (
            len(chunk_ids) != len(set(chunk_ids))
            or settings["chunk_set_sha256"] != _sha256_json(sorted(chunk_ids))
            or settings["record_root_sha256"] != _sha256_json(record_identities)
            or settings["generation_id"] != _generation_id(settings)
        ):
            raise FaissExactIndexCorruptionError(
                "FAISS exact generation identity does not match stored records"
            )
        manifest = FaissExactIndexManifest(
            generation_id=settings["generation_id"],
            model_lock_artifact_id=settings["model_lock_artifact_id"],
            vector_count=vector_count,
            dimension=dimension,
            chunk_set_sha256=settings["chunk_set_sha256"],
            record_root_sha256=settings["record_root_sha256"],
            index_sha256=settings["index_sha256"],
            faiss_version=settings["faiss_version"],
            numpy_version=settings["numpy_version"],
        )
        return manifest, index, tuple(stored_records)

    def query(
        self,
        vector: Sequence[float],
        *,
        top_k: int = 10,
        filters: Mapping[str, MetadataValue] | None = None,
        metadata_filter: MetadataFilter | None = None,
    ) -> tuple[FaissExactSearchResult, ...]:
        """Return exact inner-product results with deterministic tie breaking."""

        _, numpy = _require_runtime()
        if not 1 <= top_k <= 1000:
            raise ValueError("top_k must be between 1 and 1000")
        if filters is not None and metadata_filter is not None:
            raise ValueError("legacy and typed metadata filters are mutually exclusive")
        normalized_filters = _validated_metadata(filters or {})
        query = _normalize_vector(vector, dimension=self._manifest.dimension)
        scores, positions = self._index.search(
            numpy.ascontiguousarray(query.reshape(1, -1)),
            self._manifest.vector_count,
        )
        candidates: list[tuple[float, _StoredRecord]] = []
        for position, score in zip(positions[0], scores[0], strict=True):
            if position < 0:
                continue
            record = self._records[int(position)]
            if any(
                key not in record.metadata or record.metadata[key] != value
                for key, value in normalized_filters.items()
            ):
                continue
            if metadata_filter is not None and not matches_metadata_filter(
                record.metadata, metadata_filter
            ):
                continue
            candidates.append((float(score), record))
        candidates.sort(key=lambda candidate: (-candidate[0], candidate[1].chunk_id))
        return tuple(
            FaissExactSearchResult(
                rank=rank,
                score=score,
                chunk_id=record.chunk_id,
                metadata=record.metadata,
            )
            for rank, (score, record) in enumerate(candidates[:top_k], start=1)
        )

    def records(self) -> tuple[DenseVectorRecord, ...]:
        """Reconstruct canonical normalized records for immutable derivation."""

        return tuple(
            DenseVectorRecord(
                chunk_id=record.chunk_id,
                vector=tuple(
                    float(value) for value in self._index.reconstruct(record.position)
                ),
                metadata=record.metadata,
            )
            for record in self._records
        )


__all__ = [
    "BACKEND_ID",
    "DenseVectorRecord",
    "FaissExactIndex",
    "FaissExactIndexCorruptionError",
    "FaissExactIndexError",
    "FaissExactIndexManifest",
    "FaissExactIndexUnavailableError",
    "FaissExactSearchResult",
    "MetadataValue",
    "normalized_vector_sha256",
]
