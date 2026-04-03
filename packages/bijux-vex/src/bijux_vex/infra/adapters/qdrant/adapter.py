# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import time
from typing import Any
import uuid

try:  # pragma: no cover - optional dependency
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
except Exception:  # pragma: no cover - optional dependency
    QdrantClient = None
    qmodels = None

from bijux_vex.core.errors import BackendCapabilityError, ValidationError
from bijux_vex.infra.adapters.vectorstore import VectorStoreAdapter


@dataclass(frozen=True)
class QdrantOptions:
    collection: str
    batch_size: int
    retry_count: int
    backoff_ms: int
    api_key: str | None
    timeout: float | None
    filter_payload: dict[str, Any] | None


class QdrantVectorStoreAdapter(VectorStoreAdapter):
    backend = "qdrant"
    is_noop = False

    def __init__(
        self, uri: str | None = None, options: Mapping[str, str] | None = None
    ) -> None:
        if QdrantClient is None:  # pragma: no cover - handled by registry availability
            raise ImportError("qdrant-client is not available")
        self._options_raw = dict(options or {})
        self._opts = self._parse_options(self._options_raw)
        self._uri = uri or "http://localhost:6333"
        self._client: Any | None = None
        self._dimension: int | None = None

    @property
    def options(self) -> dict[str, str]:
        return dict(self._options_raw)

    @property
    def index_params(self) -> dict[str, object]:
        return {
            "collection": self._opts.collection,
            "batch_size": self._opts.batch_size,
            "retry_count": self._opts.retry_count,
            "backoff_ms": self._opts.backoff_ms,
            "timeout": self._opts.timeout,
        }

    def connect(self) -> None:
        if QdrantClient is None:  # pragma: no cover - defensive
            raise ImportError("qdrant-client is not available")
        if self._uri in {":memory:", "memory"}:
            self._client = QdrantClient(":memory:")
        else:
            self._client = QdrantClient(
                url=self._uri,
                api_key=self._opts.api_key,
                timeout=self._opts.timeout,
            )

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
        self._ensure_collection(len(vectors_list[0]))
        ids: list[str] = []
        payloads: list[dict[str, Any]] = []
        for entry in meta_list:
            vector_id = entry.get("vector_id")
            if vector_id is None:
                raise ValidationError(message="vector_id required for Qdrant inserts")
            vector_id_str = str(vector_id)
            ids.append(vector_id_str)
            payload = dict(entry)
            payload.setdefault("vector_id", vector_id_str)
            payloads.append(payload)
        points = [
            qmodels.PointStruct(
                id=self._qdrant_id(vector_id), vector=vector, payload=payload
            )
            for vector_id, vector, payload in zip(
                ids, vectors_list, payloads, strict=False
            )
        ]
        self._upsert(points)
        return ids

    def query(
        self, vector: Sequence[float], k: int, mode: str
    ) -> list[tuple[str, float]]:
        if self._client is None:
            raise BackendCapabilityError(message="Qdrant client is not connected")
        if mode == "deterministic":
            search_params = qmodels.SearchParams(hnsw_ef=0, exact=True)
        else:
            search_params = qmodels.SearchParams(hnsw_ef=128, exact=False)
        qfilter = None
        if self._opts.filter_payload:
            try:
                qfilter = qmodels.Filter.model_validate(self._opts.filter_payload)
            except Exception:
                qfilter = qmodels.Filter(**self._opts.filter_payload)
        results = self._client.search(
            collection_name=self._opts.collection,
            query_vector=list(vector),
            limit=int(k),
            with_payload=True,
            search_params=search_params,
            query_filter=qfilter,
        )
        output: list[tuple[str, float]] = []
        for item in results:
            payload = getattr(item, "payload", None) or {}
            vector_id = payload.get("vector_id", str(item.id))
            output.append((str(vector_id), float(item.score)))
        return output

    def delete(self, ids: Iterable[str]) -> int:
        if self._client is None:
            raise BackendCapabilityError(message="Qdrant client is not connected")
        ids_list = [self._qdrant_id(str(vector_id)) for vector_id in ids]
        if not ids_list:
            return 0
        self._client.delete(
            collection_name=self._opts.collection,
            points_selector=qmodels.PointIdsList(points=ids_list),
        )
        return len(ids_list)

    def status(self) -> dict[str, object]:
        if self._client is None:
            raise BackendCapabilityError(message="Qdrant client is not connected")
        info = self._client.get_collection(self._opts.collection)
        vectors_count = getattr(info.points_count, "count", info.points_count)
        return {
            "reachable": True,
            "backend": self.backend,
            "version": getattr(info, "status", None),
            "index": {
                "vector_count": int(vectors_count or 0),
                "deleted_count": 0,
                "dimension": self._dimension,
                "metric": "cosine",
                "index_type": "hnsw",
            },
            "operation": {
                "batch_size": self._opts.batch_size,
                "retry_count": self._opts.retry_count,
                "backoff_ms": self._opts.backoff_ms,
            },
        }

    def _ensure_collection(self, dimension: int) -> None:
        if self._client is None:
            raise BackendCapabilityError(message="Qdrant client is not connected")
        if self._dimension is None:
            self._dimension = dimension
        if self._client.collection_exists(self._opts.collection):
            return
        vectors_config = qmodels.VectorParams(
            size=dimension, distance=qmodels.Distance.COSINE
        )
        self._client.create_collection(
            collection_name=self._opts.collection,
            vectors_config=vectors_config,
        )

    def _upsert(self, points: list[Any]) -> None:
        if self._client is None:
            raise BackendCapabilityError(message="Qdrant client is not connected")
        batch = int(self._opts.batch_size)
        retries = int(self._opts.retry_count)
        backoff = int(self._opts.backoff_ms)
        idx = 0
        while idx < len(points):
            chunk = points[idx : idx + batch]
            attempt = 0
            retry_all = False
            while True:
                try:
                    self._client.upsert(
                        collection_name=self._opts.collection, points=chunk
                    )
                    if retry_all:
                        return
                    break
                except Exception as exc:
                    attempt += 1
                    if attempt > retries:
                        raise BackendCapabilityError(
                            message=f"Qdrant upsert failed after retries: {exc}"
                        ) from exc
                    retry_all = True
                    chunk = points[idx:]
                    time.sleep(backoff / 1000.0)
            idx += batch

    @staticmethod
    def _parse_options(options: Mapping[str, str]) -> QdrantOptions:
        collection = options.get("collection", "bijux_vex")
        batch_size = int(options.get("batch_size", "128"))
        retry_count = int(options.get("retry_count", "2"))
        backoff_ms = int(options.get("backoff_ms", "200"))
        api_key = options.get("api_key")
        timeout = float(options["timeout"]) if "timeout" in options else None
        filter_payload = None
        if "filter" in options:
            import json

            filter_payload = json.loads(options["filter"])
        return QdrantOptions(
            collection=collection,
            batch_size=batch_size,
            retry_count=retry_count,
            backoff_ms=backoff_ms,
            api_key=api_key,
            timeout=timeout,
            filter_payload=filter_payload,
        )

    @staticmethod
    def _qdrant_id(vector_id: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, vector_id))


__all__ = ["QdrantVectorStoreAdapter"]
