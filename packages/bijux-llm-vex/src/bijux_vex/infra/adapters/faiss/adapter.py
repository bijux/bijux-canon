# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Any

try:  # pragma: no cover - optional dependency
    import faiss
except Exception:  # pragma: no cover - optional dependency
    faiss = None

import numpy as np

from bijux_vex.core.errors import (
    BackendCapabilityError,
    BackendUnavailableError,
    ConflictError,
    CorruptArtifactError,
    DeterminismViolationError,
    ValidationError,
)
from bijux_vex.infra.adapters.vectorstore import VectorStoreAdapter

INDEX_VERSION = 1
EXACT_INDEX_TYPE = "IndexFlatL2"
ANN_INDEX_TYPE = "IndexHNSWFlat"
DEFAULT_METRIC = "l2"


@dataclass(frozen=True)
class FaissRecord:
    vector_id: str
    vector: tuple[float, ...]
    metadata: dict[str, str]


class FaissIndexLock:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._fd: int | None = None

    def __enter__(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(self._path, os.O_CREAT | os.O_RDWR)
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._fd = fd
        except OSError as exc:
            raise BackendUnavailableError(
                message=(
                    "Vector store lock is held by another process. "
                    "Wait for the lock to release or choose a different URI."
                )
            ) from exc

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._fd is None:
            return
        try:
            import fcntl

            fcntl.flock(self._fd, fcntl.LOCK_UN)
        finally:
            os.close(self._fd)
            self._fd = None


class FaissVectorStoreAdapter(VectorStoreAdapter):
    backend = "faiss"
    is_noop = False

    def __init__(
        self, uri: str | None = None, options: Mapping[str, str] | None = None
    ) -> None:
        if faiss is None:  # pragma: no cover - handled by registry availability
            raise ImportError("faiss is not available")
        self._options = dict(options or {})
        self._index: Any | None = None
        self._dimension: int | None = None
        self._records: list[FaissRecord] = []
        self._index_path = Path(uri) if uri else None
        self._meta_path = (
            self._index_path.with_suffix(".meta.json") if self._index_path else None
        )
        self._records_path = (
            self._index_path.with_suffix(".records.json") if self._index_path else None
        )
        self._lock_path = (
            self._index_path.with_suffix(".lock") if self._index_path else None
        )
        self._index_kind = self._resolve_index_kind(self._options.get("index_type"))

    @property
    def options(self) -> dict[str, str]:
        return dict(self._options)

    @property
    def index_params(self) -> dict[str, object]:
        return {
            "type": self._index_type_name(),
            "dimension": self._dimension,
            "metric": DEFAULT_METRIC,
            "ntotal": int(self._index.ntotal) if self._index is not None else 0,
            "index_version": INDEX_VERSION,
            "index_kind": self._index_kind,
        }

    @property
    def backend_version(self) -> str | None:
        return getattr(faiss, "__version__", None) if faiss is not None else None

    def connect(self) -> None:
        if faiss is None:  # pragma: no cover - defensive
            raise ImportError("faiss is not available")
        if not self._index_path:
            return
        if not self._index_path.exists():
            return
        self._load_state()

    def insert(
        self,
        vectors: Iterable[Sequence[float]],
        metadata: Iterable[dict[str, Any]] | None = None,
    ) -> list[str]:
        vectors_list = [list(vec) for vec in vectors]
        if not vectors_list:
            return []
        meta_list = list(metadata or [])
        if len(meta_list) != len(vectors_list):
            raise ValidationError(message="metadata length must match vectors length")
        vector_ids: list[str] = []
        records: list[FaissRecord] = []
        for entry, vec in zip(meta_list, vectors_list, strict=False):
            vector_id = entry.get("vector_id")
            if vector_id is None:
                raise ValidationError(message="vector_id required for FAISS inserts")
            vector_ids.append(str(vector_id))
            records.append(
                FaissRecord(
                    vector_id=str(vector_id),
                    vector=tuple(float(v) for v in vec),
                    metadata={
                        str(k): str(v) for k, v in entry.items() if v is not None
                    },
                )
            )
        dim = len(vectors_list[0])
        self._ensure_index(dim)
        if self._dimension is None:
            self._dimension = dim
        if dim != self._dimension:
            raise ValidationError(message="Vector dimensionality mismatch for FAISS")
        if len(set(vector_ids)) != len(vector_ids):
            raise ConflictError(message="Duplicate vector_id detected in insert batch")
        existing_ids = {record.vector_id for record in self._records}
        overlap = existing_ids.intersection(vector_ids)
        if overlap:
            raise ConflictError(
                message="Vector store already contains one or more vector_id values"
            )
        if self._lock_path:
            with FaissIndexLock(self._lock_path):
                self._append_records(records)
                self._add_to_index(vectors_list)
                self._persist()
        else:
            self._append_records(records)
            self._add_to_index(vectors_list)
            self._persist()
        return vector_ids

    def query(
        self, vector: Sequence[float], k: int, mode: str
    ) -> list[tuple[str, float]]:
        if self._index is None or self._index.ntotal == 0:
            return []
        if "filter" in self._options:
            raise BackendCapabilityError(
                message="Filtering is not supported by the FAISS adapter"
            )
        self._enforce_mode(mode)
        array = np.asarray([vector], dtype="float32")
        distances, indices = self._index.search(array, int(k))
        results: list[tuple[str, float]] = []
        for idx, dist in zip(indices[0], distances[0], strict=False):
            if idx < 0:
                continue
            if idx >= len(self._records):
                raise CorruptArtifactError(
                    message="FAISS index references out-of-range vector id"
                )
            vector_id = self._records[idx].vector_id
            results.append((vector_id, float(dist)))
        return results

    def delete(self, ids: Iterable[str]) -> int:
        if not self._records:
            return 0
        ids_set = {str(vector_id) for vector_id in ids}
        if not ids_set:
            return 0
        if self._lock_path:
            with FaissIndexLock(self._lock_path):
                return self._delete_records(ids_set)
        return self._delete_records(ids_set)

    def rebuild(self, *, index_type: str | None = None) -> dict[str, object]:
        if not self._index_path:
            raise ValidationError(message="FAISS rebuild requires a persistent URI")
        if self._lock_path:
            with FaissIndexLock(self._lock_path):
                return self._rebuild(index_type=index_type)
        return self._rebuild(index_type=index_type)

    def status(self) -> dict[str, object]:
        return {
            "reachable": True,
            "backend": self.backend,
            "version": self.backend_version,
            "index": {
                "vector_count": len(self._records),
                "deleted_count": 0,
                "dimension": self._dimension,
                "metric": DEFAULT_METRIC,
                "index_type": self._index_type_name(),
                "index_version": INDEX_VERSION,
            },
        }

    def _load_state(self) -> None:
        if not self._index_path or not self._meta_path or not self._records_path:
            return
        if not self._meta_path.exists():
            raise CorruptArtifactError(message="Missing FAISS metadata file")
        if not self._records_path.exists():
            raise CorruptArtifactError(message="Missing FAISS records file")
        meta = json.loads(self._meta_path.read_text(encoding="utf-8"))
        self._validate_meta(meta)
        try:
            self._index = faiss.read_index(str(self._index_path))
        except Exception as exc:  # pragma: no cover - faiss error path
            raise CorruptArtifactError(message="FAISS index failed to load") from exc
        self._dimension = int(self._index.d)
        if meta.get("dimension") != self._dimension:
            raise CorruptArtifactError(message="FAISS index dimensionality mismatch")
        if meta.get("index_type") != self._index_type_name():
            raise CorruptArtifactError(message="FAISS index type mismatch")
        records_payload = json.loads(self._records_path.read_text(encoding="utf-8"))
        self._records = [
            FaissRecord(
                vector_id=str(entry["vector_id"]),
                vector=tuple(float(v) for v in entry["vector"]),
                metadata={
                    str(k): str(v)
                    for k, v in (entry.get("metadata") or {}).items()
                    if v is not None
                },
            )
            for entry in records_payload
        ]
        if len(self._records) != int(self._index.ntotal):
            raise CorruptArtifactError(message="FAISS index/record count mismatch")

    def _append_records(self, records: list[FaissRecord]) -> None:
        self._records.extend(records)

    def _add_to_index(self, vectors_list: list[list[float]]) -> None:
        if self._index is None:
            raise CorruptArtifactError(message="FAISS index missing during insert")
        array = np.asarray(vectors_list, dtype="float32")
        self._index.add(array)

    def _delete_records(self, ids_set: set[str]) -> int:
        if not ids_set:
            return 0
        remaining = [rec for rec in self._records if rec.vector_id not in ids_set]
        removed = len(self._records) - len(remaining)
        if removed == 0:
            return 0
        self._records = remaining
        self._rebuild_index_from_records()
        self._persist()
        return removed

    def _rebuild(self, *, index_type: str | None = None) -> dict[str, object]:
        if index_type:
            self._index_kind = self._resolve_index_kind(index_type)
        self._rebuild_index_from_records()
        self._persist()
        return self.status()

    def _rebuild_index_from_records(self) -> None:
        if not self._records:
            self._index = None
            self._dimension = None
            return
        vectors = [list(rec.vector) for rec in self._records]
        self._dimension = len(vectors[0])
        self._index = self._build_index(self._dimension, self._index_kind)
        self._index.add(np.asarray(vectors, dtype="float32"))

    def _persist(self) -> None:
        if not self._index_path or not self._meta_path or not self._records_path:
            return
        if not self._records or self._index is None:
            for path in (self._index_path, self._meta_path, self._records_path):
                if path.exists():
                    path.unlink(missing_ok=True)
            return
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        meta = {
            "index_version": INDEX_VERSION,
            "faiss_version": self.backend_version,
            "metric": DEFAULT_METRIC,
            "dimension": self._dimension,
            "index_type": self._index_type_name(),
            "index_kind": self._index_kind,
        }
        records_payload = [
            {
                "vector_id": rec.vector_id,
                "vector": list(rec.vector),
                "metadata": rec.metadata,
            }
            for rec in self._records
        ]
        with tempfile.NamedTemporaryFile(
            mode="wb", delete=False, dir=self._index_path.parent
        ) as tmp_index:
            tmp_index_path = Path(tmp_index.name)
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, dir=self._index_path.parent, encoding="utf-8"
        ) as tmp_meta:
            tmp_meta_path = Path(tmp_meta.name)
            tmp_meta.write(json.dumps(meta, indent=2))
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, dir=self._index_path.parent, encoding="utf-8"
        ) as tmp_records:
            tmp_records_path = Path(tmp_records.name)
            tmp_records.write(json.dumps(records_payload, indent=2))
        try:
            faiss.write_index(self._index, str(tmp_index_path))
            tmp_index_path.replace(self._index_path)
            tmp_meta_path.replace(self._meta_path)
            tmp_records_path.replace(self._records_path)
        finally:
            for path in (tmp_index_path, tmp_meta_path, tmp_records_path):
                if path.exists():
                    path.unlink(missing_ok=True)

    def _ensure_index(self, dimension: int) -> None:
        if self._index is not None:
            return
        if self._records_path and self._records_path.exists():
            self._load_state()
            return
        self._dimension = dimension
        self._index = self._build_index(dimension, self._index_kind)

    def _build_index(self, dimension: int, index_kind: str) -> Any:
        if index_kind == "ann":
            return faiss.IndexHNSWFlat(dimension, 32)
        return faiss.IndexFlatL2(dimension)

    def _index_type_name(self) -> str:
        if self._index is None:
            return EXACT_INDEX_TYPE if self._index_kind == "exact" else ANN_INDEX_TYPE
        return type(self._index).__name__

    def _resolve_index_kind(self, raw: str | None) -> str:
        if not raw:
            return "exact"
        key = raw.lower()
        if key in {"exact", "flat", EXACT_INDEX_TYPE.lower()}:
            return "exact"
        if key in {"ann", "hnsw", ANN_INDEX_TYPE.lower()}:
            return "ann"
        raise ValidationError(message=f"Unknown FAISS index_type: {raw}")

    def _validate_meta(self, meta: dict[str, Any]) -> None:
        if meta.get("index_version") != INDEX_VERSION:
            raise CorruptArtifactError(message="FAISS index version mismatch")
        if meta.get("faiss_version") != self.backend_version:
            raise CorruptArtifactError(message="FAISS version mismatch")
        if meta.get("metric") != DEFAULT_METRIC:
            raise CorruptArtifactError(message="FAISS metric mismatch")
        index_kind = meta.get("index_kind")
        if index_kind:
            self._index_kind = self._resolve_index_kind(str(index_kind))

    def _enforce_mode(self, mode: str) -> None:
        if mode == "deterministic" and self._index_kind != "exact":
            raise DeterminismViolationError(
                message="Deterministic execution requires an exact FAISS index",
                invariant_id="INV-FAISS-MODE-001",
            )
        if mode != "deterministic" and self._index_kind != "ann":
            raise DeterminismViolationError(
                message="Non-deterministic execution requires an ANN FAISS index",
                invariant_id="INV-FAISS-MODE-002",
            )


__all__ = ["FaissVectorStoreAdapter", "FaissRecord"]
