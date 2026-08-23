# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Persistent seeded FAISS HNSW generations with exact recall witnesses."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
from typing import Any

from bijux_canon_index.domain.metadata_filters import (
    MetadataFilter,
    matches_metadata_filter,
)
from bijux_canon_index.infra.adapters.faiss.exact import (
    DenseVectorRecord,
    FaissExactIndex,
    MetadataValue,
    _canonical_json,
    _normalize_vector,
    _require_runtime,
    _sha256_bytes,
    _sha256_json,
    _StoredRecord,
    _validated_metadata,
    _vector_sha256,
)
from bijux_canon_index.infra.runtime_paths import ensure_parent_dir

SCHEMA_VERSION = 1
BACKEND_ID = "faiss-hnsw"
INDEX_TYPE = "IndexHNSWFlat"
METRIC = "inner_product"
NORMALIZATION = "l2-float32-v1"
SEED_BEHAVIOR = "faiss-random-generator-single-thread-build-v1"

_BUILD_LOCK = threading.Lock()


class FaissHnswIndexError(RuntimeError):
    """Base failure for approximate dense generation operations."""


class FaissHnswIndexCorruptionError(FaissHnswIndexError):
    """A stored HNSW generation failed content verification."""


@dataclass(frozen=True, slots=True)
class HnswParameters:
    """Construction and fixed query effort for one HNSW generation."""

    m: int = 32
    ef_construction: int = 200
    ef_search: int = 64
    seed: int = 42

    def __post_init__(self) -> None:
        if not 2 <= self.m <= 128:
            raise ValueError("HNSW M must be within 2..128")
        if not self.m <= self.ef_construction <= 4096:
            raise ValueError("HNSW construction effort must be within M..4096")
        if not 1 <= self.ef_search <= 4096:
            raise ValueError("HNSW search effort must be within 1..4096")
        if not 0 <= self.seed <= 2_147_483_647:
            raise ValueError("HNSW seed must be a non-negative 32-bit integer")


@dataclass(frozen=True, slots=True)
class FaissHnswSearchResult:
    """One approximate result with a stable chunk mapping."""

    rank: int
    score: float
    chunk_id: str
    metadata: Mapping[str, MetadataValue]


@dataclass(frozen=True, slots=True)
class FaissHnswIndexManifest:
    """Complete content, runtime, and effort identity for one HNSW graph."""

    generation_id: str
    model_lock_artifact_id: str
    vector_count: int
    dimension: int
    chunk_set_sha256: str
    record_root_sha256: str
    index_sha256: str
    parameters_sha256: str
    parameters: HnswParameters
    faiss_version: str
    numpy_version: str
    index_type: str = INDEX_TYPE
    metric: str = METRIC
    normalization: str = NORMALIZATION
    seed_behavior: str = SEED_BEHAVIOR


@dataclass(frozen=True, slots=True)
class HnswRecallMeasurement:
    """Measured approximation quality against exact-search witnesses."""

    query_count: int
    k: int
    mean_recall: float
    minimum_recall: float
    result_reachability: float
    maximum_score_delta: float


def _parameter_payload(parameters: HnswParameters) -> dict[str, int | str]:
    return {
        "ef_construction": parameters.ef_construction,
        "ef_search": parameters.ef_search,
        "m": parameters.m,
        "seed": parameters.seed,
        "seed_behavior": SEED_BEHAVIOR,
    }


def _generation_id(settings: Mapping[str, str]) -> str:
    identity = {key: value for key, value in settings.items() if key != "generation_id"}
    return f"sha256:{_sha256_json(identity)}"


class FaissHnswIndex:
    """Read-only API over one atomically published FAISS HNSW generation."""

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
                check_same_thread=False,
            )
            self._connection.execute("PRAGMA busy_timeout=5000")
            self._manifest, self._index, self._records = self._verify()
        except FaissHnswIndexError:
            connection = getattr(self, "_connection", None)
            if connection is not None:
                connection.close()
            raise
        except sqlite3.DatabaseError as error:
            connection = getattr(self, "_connection", None)
            if connection is not None:
                connection.close()
            raise FaissHnswIndexCorruptionError(
                "FAISS HNSW generation container is unreadable or corrupt"
            ) from error

    @classmethod
    def build(
        cls,
        path: str | Path,
        records: Iterable[DenseVectorRecord],
        *,
        model_lock_artifact_id: str,
        parameters: HnswParameters | None = None,
        replace: bool = False,
    ) -> FaissHnswIndex:
        """Build and atomically publish a complete seeded HNSW generation."""

        _require_runtime()
        if not model_lock_artifact_id:
            raise ValueError("an HNSW generation requires a model lock identity")
        resolved_parameters = parameters or HnswParameters()
        destination = ensure_parent_dir(path)
        if destination.exists() and not replace:
            raise FileExistsError(destination)
        admitted = sorted(records, key=lambda record: record.chunk_id)
        if not admitted:
            raise ValueError("an HNSW generation requires at least one vector")
        chunk_ids = [record.chunk_id for record in admitted]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("chunk identities must be unique within a generation")
        dimension = len(admitted[0].vector)
        if any(len(record.vector) != dimension for record in admitted):
            raise ValueError("all HNSW vectors must have the same dimension")

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
                parameters=resolved_parameters,
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
        parameters: HnswParameters,
    ) -> None:
        faiss_runtime, numpy = _require_runtime()
        dimension = len(records[0].vector)
        vectors = numpy.stack(
            [
                _normalize_vector(record.vector, dimension=dimension)
                for record in records
            ]
        ).astype("float32", copy=False)
        with _BUILD_LOCK:
            previous_threads = int(faiss_runtime.omp_get_max_threads())
            faiss_runtime.omp_set_num_threads(1)
            try:
                index = faiss_runtime.IndexHNSWFlat(
                    dimension,
                    parameters.m,
                    faiss_runtime.METRIC_INNER_PRODUCT,
                )
                index.hnsw.efConstruction = parameters.ef_construction
                index.hnsw.efSearch = parameters.ef_search
                index.hnsw.rng = faiss_runtime.RandomGenerator(parameters.seed)
                index.add(vectors)
            finally:
                faiss_runtime.omp_set_num_threads(previous_threads)
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
        parameter_payload = _parameter_payload(parameters)
        settings = {
            "backend": BACKEND_ID,
            "chunk_set_sha256": _sha256_json([record.chunk_id for record in records]),
            "dimension": str(dimension),
            "ef_construction": str(parameters.ef_construction),
            "ef_search": str(parameters.ef_search),
            "faiss_version": str(getattr(faiss_runtime, "__version__", "unknown")),
            "hnsw_m": str(parameters.m),
            "index_sha256": index_sha256,
            "index_type": INDEX_TYPE,
            "metric": METRIC,
            "model_lock_artifact_id": model_lock_artifact_id,
            "normalization": NORMALIZATION,
            "numpy_version": str(numpy.__version__),
            "parameters_sha256": _sha256_json(parameter_payload),
            "record_root_sha256": _sha256_json(record_identities),
            "seed": str(parameters.seed),
            "seed_behavior": SEED_BEHAVIOR,
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
                CREATE TABLE hnsw_generation(
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                ) WITHOUT ROWID;
                CREATE TABLE hnsw_index(
                    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
                    serialized_index BLOB NOT NULL,
                    index_sha256 TEXT NOT NULL
                );
                CREATE TABLE hnsw_records(
                    position INTEGER PRIMARY KEY CHECK(position >= 0),
                    chunk_id TEXT NOT NULL UNIQUE,
                    metadata_json TEXT NOT NULL,
                    vector_sha256 TEXT NOT NULL
                );
                """
            )
            with connection:
                connection.executemany(
                    "INSERT INTO hnsw_generation(key, value) VALUES(?, ?)",
                    sorted(settings.items()),
                )
                connection.execute(
                    """
                    INSERT INTO hnsw_index(
                        singleton, serialized_index, index_sha256
                    ) VALUES(1, ?, ?)
                    """,
                    (index_bytes, index_sha256),
                )
                connection.executemany(
                    """
                    INSERT INTO hnsw_records(
                        position, chunk_id, metadata_json, vector_sha256
                    ) VALUES(?, ?, ?, ?)
                    """,
                    stored_records,
                )
        finally:
            connection.close()

    @property
    def manifest(self) -> FaissHnswIndexManifest:
        """Return the verified immutable HNSW generation identity."""

        return self._manifest

    def close(self) -> None:
        """Close the generation container."""

        self._connection.close()

    def __enter__(self) -> FaissHnswIndex:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _settings(self) -> dict[str, str]:
        return {
            str(key): str(value)
            for key, value in self._connection.execute(
                "SELECT key, value FROM hnsw_generation ORDER BY key"
            )
        }

    def _verify(self) -> tuple[FaissHnswIndexManifest, Any, tuple[_StoredRecord, ...]]:
        faiss_runtime, numpy = _require_runtime()
        if self._connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise FaissHnswIndexCorruptionError(
                "FAISS HNSW generation failed database integrity checks"
            )
        if self._connection.execute("PRAGMA user_version").fetchone() != (
            SCHEMA_VERSION,
        ):
            raise FaissHnswIndexCorruptionError(
                "FAISS HNSW generation schema version is unsupported"
            )
        settings = self._settings()
        expected_keys = {
            "backend",
            "chunk_set_sha256",
            "dimension",
            "ef_construction",
            "ef_search",
            "faiss_version",
            "generation_id",
            "hnsw_m",
            "index_sha256",
            "index_type",
            "metric",
            "model_lock_artifact_id",
            "normalization",
            "numpy_version",
            "parameters_sha256",
            "record_root_sha256",
            "seed",
            "seed_behavior",
            "vector_count",
        }
        if set(settings) != expected_keys:
            raise FaissHnswIndexCorruptionError(
                "FAISS HNSW generation metadata is incomplete"
            )
        if (
            settings["backend"] != BACKEND_ID
            or settings["index_type"] != INDEX_TYPE
            or settings["metric"] != METRIC
            or settings["normalization"] != NORMALIZATION
            or settings["seed_behavior"] != SEED_BEHAVIOR
            or settings["faiss_version"]
            != str(getattr(faiss_runtime, "__version__", "unknown"))
            or settings["numpy_version"] != str(numpy.__version__)
        ):
            raise FaissHnswIndexCorruptionError(
                "FAISS HNSW generation backend identity drifted"
            )
        try:
            dimension = int(settings["dimension"])
            vector_count = int(settings["vector_count"])
            parameters = HnswParameters(
                m=int(settings["hnsw_m"]),
                ef_construction=int(settings["ef_construction"]),
                ef_search=int(settings["ef_search"]),
                seed=int(settings["seed"]),
            )
        except ValueError as error:
            raise FaissHnswIndexCorruptionError(
                "FAISS HNSW generation parameters are invalid"
            ) from error
        if dimension < 1 or vector_count < 1:
            raise FaissHnswIndexCorruptionError(
                "FAISS HNSW generation dimensions are invalid"
            )
        if settings["parameters_sha256"] != _sha256_json(
            _parameter_payload(parameters)
        ):
            raise FaissHnswIndexCorruptionError("FAISS HNSW parameter checksum failed")

        index_row = self._connection.execute(
            "SELECT serialized_index, index_sha256 FROM hnsw_index WHERE singleton=1"
        ).fetchone()
        if index_row is None:
            raise FaissHnswIndexCorruptionError(
                "FAISS HNSW generation is missing its serialized index"
            )
        index_bytes, stored_index_sha256 = index_row
        if (
            not isinstance(index_bytes, bytes)
            or stored_index_sha256 != _sha256_bytes(index_bytes)
            or settings["index_sha256"] != stored_index_sha256
        ):
            raise FaissHnswIndexCorruptionError(
                "FAISS HNSW serialized index checksum failed"
            )
        try:
            index = faiss_runtime.deserialize_index(
                numpy.frombuffer(index_bytes, dtype="uint8")
            )
        except Exception as error:
            raise FaissHnswIndexCorruptionError(
                "FAISS HNSW serialized index failed to load"
            ) from error
        if (
            type(index).__name__ != INDEX_TYPE
            or int(index.d) != dimension
            or int(index.ntotal) != vector_count
            or int(index.metric_type) != int(faiss_runtime.METRIC_INNER_PRODUCT)
            or int(index.hnsw.nb_neighbors(1)) != parameters.m
            or int(index.hnsw.efConstruction) != parameters.ef_construction
            or int(index.hnsw.efSearch) != parameters.ef_search
        ):
            raise FaissHnswIndexCorruptionError(
                "FAISS HNSW graph parameters do not match its manifest"
            )

        rows = self._connection.execute(
            """
            SELECT position, chunk_id, metadata_json, vector_sha256
            FROM hnsw_records ORDER BY position
            """
        ).fetchall()
        if len(rows) != vector_count:
            raise FaissHnswIndexCorruptionError(
                "FAISS HNSW chunk mapping count does not match the graph"
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
            raise FaissHnswIndexCorruptionError(
                "FAISS HNSW chunk mapping or vector checksum failed"
            ) from error
        if (
            len(chunk_ids) != len(set(chunk_ids))
            or settings["chunk_set_sha256"] != _sha256_json(sorted(chunk_ids))
            or settings["record_root_sha256"] != _sha256_json(record_identities)
            or settings["generation_id"] != _generation_id(settings)
        ):
            raise FaissHnswIndexCorruptionError(
                "FAISS HNSW generation identity does not match stored records"
            )
        manifest = FaissHnswIndexManifest(
            generation_id=settings["generation_id"],
            model_lock_artifact_id=settings["model_lock_artifact_id"],
            vector_count=vector_count,
            dimension=dimension,
            chunk_set_sha256=settings["chunk_set_sha256"],
            record_root_sha256=settings["record_root_sha256"],
            index_sha256=settings["index_sha256"],
            parameters_sha256=settings["parameters_sha256"],
            parameters=parameters,
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
    ) -> tuple[FaissHnswSearchResult, ...]:
        """Return approximate inner-product results with stable tie breaking."""

        _, numpy = _require_runtime()
        if not 1 <= top_k <= 1000:
            raise ValueError("top_k must be between 1 and 1000")
        if filters is not None and metadata_filter is not None:
            raise ValueError("legacy and typed metadata filters are mutually exclusive")
        normalized_filters = _validated_metadata(filters or {})
        query = _normalize_vector(vector, dimension=self._manifest.dimension)
        search_count = (
            self._manifest.vector_count
            if normalized_filters or metadata_filter is not None
            else min(
                self._manifest.vector_count,
                max(top_k, self._manifest.parameters.ef_search),
            )
        )
        scores, positions = self._index.search(
            numpy.ascontiguousarray(query.reshape(1, -1)),
            search_count,
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
            FaissHnswSearchResult(
                rank=rank,
                score=score,
                chunk_id=record.chunk_id,
                metadata=record.metadata,
            )
            for rank, (score, record) in enumerate(candidates[:top_k], start=1)
        )

    def chunk_ids(self) -> tuple[str, ...]:
        """Return the verified chunk mapping in canonical position order."""

        return tuple(record.chunk_id for record in self._records)


def measure_hnsw_recall(
    approximate: FaissHnswIndex,
    exact: FaissExactIndex,
    queries: Sequence[Sequence[float]],
    *,
    k: int,
) -> HnswRecallMeasurement:
    """Measure one HNSW generation against its exact-search witness."""

    if not queries:
        raise ValueError("HNSW recall measurement requires at least one query")
    if k < 1 or k > min(
        approximate.manifest.vector_count,
        exact.manifest.vector_count,
    ):
        raise ValueError("HNSW recall k exceeds the compared generations")
    if (
        approximate.manifest.model_lock_artifact_id
        != exact.manifest.model_lock_artifact_id
        or approximate.manifest.dimension != exact.manifest.dimension
        or approximate.manifest.chunk_set_sha256 != exact.manifest.chunk_set_sha256
    ):
        raise ValueError("HNSW and exact witness generations are incompatible")

    recalls = []
    reached = 0
    score_deltas: list[float] = []
    for query in queries:
        exact_results = exact.query(query, top_k=k)
        approximate_results = approximate.query(query, top_k=k)
        exact_ids = {result.chunk_id for result in exact_results}
        approximate_ids = {result.chunk_id for result in approximate_results}
        recalls.append(len(exact_ids & approximate_ids) / len(exact_ids))
        reached += len(approximate_results)
        exact_scores = {result.chunk_id: result.score for result in exact_results}
        score_deltas.extend(
            abs(result.score - exact_scores[result.chunk_id])
            for result in approximate_results
            if result.chunk_id in exact_scores
        )
    return HnswRecallMeasurement(
        query_count=len(queries),
        k=k,
        mean_recall=sum(recalls) / len(recalls),
        minimum_recall=min(recalls),
        result_reachability=reached / (len(queries) * k),
        maximum_score_delta=max(score_deltas, default=0.0),
    )


__all__ = [
    "BACKEND_ID",
    "FaissHnswIndex",
    "FaissHnswIndexCorruptionError",
    "FaissHnswIndexError",
    "FaissHnswIndexManifest",
    "FaissHnswSearchResult",
    "HnswParameters",
    "HnswRecallMeasurement",
    "measure_hnsw_recall",
]
