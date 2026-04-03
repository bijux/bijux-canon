# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Iterable, Sequence
import json
from pathlib import Path
import time
from typing import Any

try:  # pragma: no cover - optional dependency
    import hnswlib
except Exception:  # pragma: no cover - optional dependency
    hnswlib = None

from bijux_vex.contracts.resources import VectorSource
from bijux_vex.core.errors import (
    AnnIndexBuildError,
    BudgetExceededError,
    CorruptArtifactError,
    ValidationError,
)
from bijux_vex.core.execution_result import ApproximationReport
from bijux_vex.core.identity.ids import fingerprint
from bijux_vex.core.types import (
    ExecutionArtifact,
    ExecutionRequest,
    NDSettings,
    Result,
    Vector,
)
from bijux_vex.infra.adapters.ann_base import AnnExecutionRequestRunner
from bijux_vex.infra.adapters.hnsw.metadata import as_dict, validate_index_meta
from bijux_vex.infra.adapters.hnsw.params import as_int, resolve_space
from bijux_vex.infra.logging import log_event


class HnswAnnRunner(AnnExecutionRequestRunner):
    """Production HNSW ANN runner backed by hnswlib with persistent indices."""

    INDEX_VERSION = 1

    def __init__(self, vectors: VectorSource, index_dir: str | Path | None = None):
        if hnswlib is None:  # pragma: no cover - optional dependency
            raise RuntimeError("hnswlib is required for HnswAnnRunner")
        self.vectors = vectors
        self._index: Any | None = None
        self._ids: list[str] = []
        self._index_info: dict[str, dict[str, object]] = {}
        self._index_dir = Path(index_dir) if index_dir else None
        if self._index_dir:
            self._index_dir.mkdir(parents=True, exist_ok=True)
        self._last_query_metadata: dict[str, object] = {}
        self._active_seed: int | None = None
        self._adaptive_ef_search: dict[str, int] = {}

    @property
    def randomness_sources(self) -> tuple[str, ...]:
        return ("hnswlib",)

    @property
    def reproducibility_bounds(self) -> str:
        return "bounded"

    @property
    def supports_seed(self) -> bool:
        return True

    @property
    def supports_compaction(self) -> bool:
        return True

    def set_randomness_profile(self, randomness: object | None) -> None:
        if randomness is None:
            self._active_seed = None
            return
        seed = getattr(randomness, "seed", None)
        if isinstance(seed, bool):
            self._active_seed = None
            return
        if isinstance(seed, (int, float)):
            self._active_seed = int(seed)
            return
        self._active_seed = None

    def approximate_request(
        self, artifact: ExecutionArtifact, request: ExecutionRequest
    ) -> Iterable[Result]:
        return self._hnsw_results(artifact, request)

    def deterministic_fallback(
        self, artifact_id: str, request: ExecutionRequest
    ) -> Iterable[Result]:
        return self.vectors.query(artifact_id, request)

    def build_index(
        self,
        artifact_id: str,
        vectors: Iterable[Vector],
        metric: str,
        nd_settings: object | None = None,
    ) -> dict[str, object]:
        vectors_list = list(vectors)
        if not vectors_list:
            return {}
        dim = vectors_list[0].dimension
        ids = [vec.vector_id for vec in vectors_list]
        settings = nd_settings if isinstance(nd_settings, NDSettings) else None
        if settings and settings.max_index_memory_mb:
            estimated_mb = (len(vectors_list) * dim * 8) / (1024 * 1024)
            if estimated_mb > float(settings.max_index_memory_mb):
                raise BudgetExceededError(
                    message="ANN index memory estimate exceeds limit",
                    dimension="memory",
                )
        space = resolve_space(metric, settings.space if settings else None)
        m_val = settings.m if settings and settings.m is not None else 16
        ef_construction = (
            settings.ef_construction if settings and settings.ef_construction else 100
        )
        ef_search = settings.ef_search if settings and settings.ef_search else 50
        if (
            settings
            and settings.max_ef_search is not None
            and ef_search > int(settings.max_ef_search)
        ):
            raise ValidationError(message="HNSW ef_search exceeds max_ef_search cap")

        build_started = time.time()
        index = hnswlib.Index(space=space, dim=dim)
        seed = self._active_seed if self._active_seed is not None else 0
        if hasattr(index, "set_seed"):
            index.set_seed(int(seed))
        index.init_index(
            max_elements=len(vectors_list),
            ef_construction=int(ef_construction),
            M=int(m_val),
        )
        index.add_items([vec.values for vec in vectors_list], list(range(len(ids))))
        index.set_ef(int(ef_search))
        self._index = index
        self._ids = ids

        index_hash = fingerprint(
            {
                "artifact_id": artifact_id,
                "ids": ids,
                "dimension": dim,
                "metric": metric,
                "space": space,
                "params": {
                    "M": int(m_val),
                    "ef_construction": int(ef_construction),
                    "ef_search": int(ef_search),
                },
                "backend_version": getattr(hnswlib, "__version__", "unknown"),
                "index_version": self.INDEX_VERSION,
            }
        )
        info: dict[str, object] = {
            "index_version": self.INDEX_VERSION,
            "index_kind": "hnswlib",
            "backend": "hnswlib",
            "index_params": {
                "M": int(m_val),
                "ef_construction": int(ef_construction),
                "ef_search": int(ef_search),
            },
            "build_time_ms": int((time.time() - build_started) * 1000),
            "vector_count": len(ids),
            "dimension": dim,
            "metric": metric,
            "space": space,
            "index_hash": index_hash,
            "backend_version": getattr(hnswlib, "__version__", "unknown"),
            "seed": int(seed),
        }
        self._index_info[artifact_id] = info
        self._persist_index(artifact_id, info)
        self._adaptive_ef_search[artifact_id] = int(ef_search)
        return info

    def index_info(self, artifact_id: str) -> dict[str, object]:
        return dict(self._index_info.get(artifact_id, {}))

    def warmup(self, artifact_id: str, queries: Iterable[Iterable[float]]) -> None:
        if self._index is None:
            return
        warm_k = 1
        for query in queries:
            try:
                if query:
                    self._index.knn_query([tuple(query)], k=warm_k)
            except Exception as exc:
                log_event("nd_warmup_query_failed", error=str(exc))

    def compact(self, artifact_id: str, vectors: Iterable[Vector], metric: str) -> None:
        self.build_index(artifact_id, vectors, metric)

    def query(
        self, vector: Iterable[float], k: int, **params: object
    ) -> tuple[list[str], list[float], dict[str, object]]:
        if self._index is None:
            raise AnnIndexBuildError(message="HNSW index not loaded")
        labels: Sequence[Sequence[int]]
        distances: Sequence[Sequence[float]]
        labels, distances = self._index.knn_query([tuple(vector)], k=k)
        return (
            [self._ids[label] for label in labels[0]],
            list(map(float, distances[0])),
            {
                "algorithm": "hnswlib",
                "index_params": self._index_info.get("index_params", ()),
                "query_params": {"k": k},
                "n_candidates": len(labels[0]),
                "random_seed": 0,
                "randomness_source": self.randomness_sources,
            },
        )

    def approximation_report(
        self,
        artifact: ExecutionArtifact,
        request: ExecutionRequest,
        results: Iterable[Result],
    ) -> ApproximationReport:
        materialized = tuple(results)
        index_info = as_dict(self._index_info.get(artifact.artifact_id))
        index_hash = index_info.get("index_hash") if index_info else None
        if index_hash is not None:
            index_hash = str(index_hash)
        index_params = as_dict(index_info.get("index_params"))
        return ApproximationReport(
            recall_at_k=0.0,
            rank_displacement=0.0,
            distance_error=0.0,
            algorithm="hnswlib",
            algorithm_version="v1",
            backend="memory",
            backend_version=str(getattr(hnswlib, "__version__", "unknown")),
            randomness_sources=self.randomness_sources,
            deterministic_fallback_used=False,
            truncation_ratio=None,
            index_parameters=tuple((str(k), str(v)) for k, v in index_params.items()),
            query_parameters=self._query_params_metadata(),
            n_candidates=len(materialized),
            random_seed=self._seed_value(),
            candidate_k=getattr(request.nd_settings, "candidate_k", None),
            index_hash=index_hash,
        )

    # ---- internals -----------------------------------------------------

    def _hnsw_results(
        self, artifact: ExecutionArtifact, request: ExecutionRequest
    ) -> Iterable[Result]:
        if self._index is None:
            try:
                self._load_index(artifact, request.nd_settings)
            except CorruptArtifactError:
                if request.nd_settings and request.nd_settings.build_on_demand:
                    vectors = list(self.vectors.list_vectors())
                    self.build_index(
                        artifact.artifact_id,
                        vectors,
                        artifact.metric,
                        request.nd_settings,
                    )
                else:
                    raise
        if (
            self._index is None
            and request.nd_settings
            and request.nd_settings.build_on_demand
        ):
            vectors = list(self.vectors.list_vectors())
            self.build_index(
                artifact.artifact_id,
                vectors,
                artifact.metric,
                request.nd_settings,
            )
        if self._index is None:
            raise AnnIndexBuildError(message="HNSW index missing; build required")
        index_info = as_dict(self._index_info.get(artifact.artifact_id))
        dim = as_int(index_info.get("dimension"), 0)
        query = request.vector or ()
        if dim and len(query) != dim:
            raise ValidationError(message="query vector dimension mismatch")
        if (
            request.execution_budget is not None
            and request.execution_budget.max_ann_probes is not None
            and request.execution_budget.max_ann_probes <= 0
        ):
            raise BudgetExceededError(
                message="ANN probes budget exhausted before execution",
                dimension="ann_probes",
            )
        if (
            request.execution_budget is not None
            and request.execution_budget.max_memory_mb is not None
            and len(self._ids) > int(request.execution_budget.max_memory_mb)
        ):
            raise BudgetExceededError(
                message="ANN candidate budget exceeded",
                dimension="candidates",
            )
        if (
            request.nd_settings
            and request.nd_settings.max_candidates is not None
            and int(request.top_k) > int(request.nd_settings.max_candidates)
        ):
            raise BudgetExceededError(
                message="ANN candidate budget exceeded",
                dimension="candidates",
            )
        index_params = as_dict(index_info.get("index_params"))
        ef_search = as_int(index_params.get("ef_search"), 50)
        if request.nd_settings and request.nd_settings.ef_search is not None:
            ef_search = int(request.nd_settings.ef_search)
        if request.nd_settings and request.nd_settings.max_ef_search is not None:
            ef_search = min(ef_search, int(request.nd_settings.max_ef_search))
        if request.nd_settings and request.nd_settings.latency_budget_ms is not None:
            adaptive = self._adaptive_ef_search.get(artifact.artifact_id)
            if adaptive:
                ef_search = min(ef_search, int(adaptive))
        if self._active_seed is not None and hasattr(self._index, "set_seed"):
            self._index.set_seed(int(self._active_seed))
        self._index.set_ef(int(ef_search))
        self._last_query_metadata = {
            "query_params": {"k": request.top_k or 1, "ef_search": ef_search},
            "seed": self._active_seed if self._active_seed is not None else 0,
        }
        start = time.time()
        labels, distances = self._index.knn_query(
            [query], k=min(request.top_k, len(self._ids))
        )
        elapsed_ms = int((time.time() - start) * 1000)
        if request.nd_settings and request.nd_settings.latency_budget_ms is not None:
            budget = float(request.nd_settings.latency_budget_ms)
            current = self._adaptive_ef_search.get(artifact.artifact_id, ef_search)
            if elapsed_ms > budget and current > 10:
                self._adaptive_ef_search[artifact.artifact_id] = max(10, current // 2)
                log_event(
                    "nd_degraded",
                    reason="latency_budget",
                    previous_ef_search=current,
                    new_ef_search=self._adaptive_ef_search[artifact.artifact_id],
                )
            elif elapsed_ms < budget * 0.5 and request.nd_settings.target_recall:
                self._adaptive_ef_search[artifact.artifact_id] = min(
                    max(current, ef_search + 10),
                    int(request.nd_settings.max_ef_search or current),
                )
        if (
            request.execution_budget is not None
            and request.execution_budget.max_latency_ms
            and elapsed_ms > int(request.execution_budget.max_latency_ms)
        ):
            raise BudgetExceededError(
                message="ANN latency budget exceeded",
                dimension="latency",
            )
        results: list[Result] = []
        for rank, (label, dist) in enumerate(
            zip(labels[0], distances[0], strict=True), start=1
        ):
            vec_id = self._ids[label]
            vector = self.vectors.get_vector(vec_id)
            chunk_id = vector.chunk_id if vector else ""
            doc_id = ""
            if vector:
                ch = self.vectors.get_chunk(vector.chunk_id)
                doc_id = ch.document_id if ch else ""
            results.append(
                Result(
                    request_id=request.request_id,
                    document_id=doc_id,
                    chunk_id=chunk_id,
                    vector_id=vec_id,
                    artifact_id=artifact.artifact_id,
                    score=float(dist),
                    rank=rank,
                )
            )
        return tuple(results)

    def _load_index(
        self, artifact: ExecutionArtifact, settings: NDSettings | None
    ) -> None:
        if self._index_dir is None:
            return
        index_file = self._index_dir / f"{artifact.artifact_id}.hnsw"
        meta_file = self._index_dir / f"{artifact.artifact_id}.json"
        if not index_file.exists() or not meta_file.exists():
            return
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover
            raise CorruptArtifactError(message="HNSW index metadata corrupted") from exc
        validate_index_meta(
            artifact,
            meta,
            settings,
            index_version=HnswAnnRunner.INDEX_VERSION,
        )
        if settings and settings.max_index_memory_mb:
            dim = int(meta.get("dimension", 0) or 0)
            count = int(meta.get("vector_count", 0) or 0)
            estimated_mb = (count * dim * 8) / (1024 * 1024)
            if estimated_mb > float(settings.max_index_memory_mb):
                raise BudgetExceededError(
                    message="ANN index memory estimate exceeds limit",
                    dimension="memory",
                )
        index = hnswlib.Index(space=meta["space"], dim=int(meta["dimension"]))
        try:
            index.load_index(str(index_file))
        except Exception as exc:  # pragma: no cover
            raise CorruptArtifactError(message="HNSW index corrupted") from exc
        self._index = index
        self._ids = list(meta.get("ids", []))
        self._index_info[artifact.artifact_id] = meta
        if meta.get("index_params", {}).get("ef_search"):
            index.set_ef(int(meta["index_params"]["ef_search"]))
        if meta.get("index_params", {}).get("ef_search"):
            self._adaptive_ef_search[artifact.artifact_id] = int(
                meta["index_params"]["ef_search"]
            )

    def _persist_index(self, artifact_id: str, info: dict[str, object]) -> None:
        if self._index_dir is None or self._index is None:
            return
        index_file = self._index_dir / f"{artifact_id}.hnsw"
        meta_file = self._index_dir / f"{artifact_id}.json"
        index_tmp = index_file.with_suffix(".hnsw.tmp")
        meta_tmp = meta_file.with_suffix(".json.tmp")
        self._index.save_index(str(index_tmp))
        meta_tmp.write_text(
            json.dumps(info, indent=2, sort_keys=True), encoding="utf-8"
        )
        index_tmp.replace(index_file)
        meta_tmp.replace(meta_file)

    def _query_params_metadata(self) -> tuple[tuple[str, str], ...]:
        params = self._last_query_metadata.get("query_params")
        if isinstance(params, dict):
            return tuple((str(k), str(v)) for k, v in params.items())
        return ()

    def _seed_value(self) -> int | None:
        seed = self._last_query_metadata.get("seed")
        if isinstance(seed, bool):
            return None
        if isinstance(seed, (int, float)):
            return int(seed)
        if isinstance(seed, str):
            try:
                return int(seed)
            except ValueError:
                return None
        return None


__all__ = ["HnswAnnRunner"]
