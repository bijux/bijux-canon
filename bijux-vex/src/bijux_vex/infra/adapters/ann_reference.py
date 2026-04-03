# SPDX-License-Identifier: MIT
# pyright: reportMissingModuleSource=false, reportMissingImports=false
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from statistics import mean
import time

from bijux_vex.contracts.resources import VectorSource
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.execution_result import ApproximationReport
from bijux_vex.core.identity.ids import fingerprint
from bijux_vex.core.types import (
    ExecutionArtifact,
    ExecutionRequest,
    Result,
    Vector,
)
from bijux_vex.infra.adapters.ann_base import AnnExecutionRequestRunner


class ReferenceAnnRunner(AnnExecutionRequestRunner):
    """Reference ANN runner that truncates deterministic results."""

    def __init__(self, vectors: VectorSource, index_dir: str | Path | None = None):
        self.vectors = vectors
        self._index_info: dict[str, dict[str, object]] = {}
        self._last_query_metadata: dict[str, object] = {}
        self._index_dir = Path(index_dir) if index_dir else None

    @property
    def randomness_sources(self) -> tuple[str, ...]:
        return ("reference_ann_truncation",)

    @property
    def reproducibility_bounds(self) -> str:
        return "bounded"

    @property
    def supports_seed(self) -> bool:
        return True

    def approximate_request(
        self, artifact: ExecutionArtifact, request: ExecutionRequest
    ) -> Iterable[Result]:
        return self._truncate_results(artifact, request)

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
        index_hash = fingerprint(
            {
                "artifact_id": artifact_id,
                "ids": ids,
                "dimension": dim,
                "metric": metric,
            }
        )
        info: dict[str, object] = {
            "index_kind": "reference",
            "index_params": {},
            "build_time_ms": int((time.time() - time.time()) * 1000),
            "vector_count": len(ids),
            "index_hash": index_hash,
            "dimension": dim,
            "metric": metric,
        }
        self._index_info[artifact_id] = info
        return info

    def index_info(self, artifact_id: str) -> dict[str, object]:
        return dict(self._index_info.get(artifact_id, {}))

    def query(
        self, vector: Iterable[float], k: int, **params: object
    ) -> tuple[list[str], list[float], dict[str, object]]:
        request = ExecutionRequest(
            request_id="ann-query",
            text=None,
            vector=tuple(vector),
            top_k=k,
            execution_contract=ExecutionContract.NON_DETERMINISTIC,
            execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
            execution_mode=ExecutionMode.BOUNDED,
        )
        stub_artifact = ExecutionArtifact(
            artifact_id="ann-stub",
            corpus_fingerprint="ann-corpus",
            vector_fingerprint="ann-vectors",
            metric="l2",
            scoring_version="v1",
            execution_contract=ExecutionContract.NON_DETERMINISTIC,
        )
        results = list(self._truncate_results(stub_artifact, request))
        return (
            [r.vector_id for r in results],
            [r.score for r in results],
            {
                "algorithm": "reference_ann_truncation",
                "index_params": (),
                "query_params": {"k": k},
                "n_candidates": len(results),
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
        exact = tuple(self.deterministic_fallback(artifact.artifact_id, request))
        exact_ids = {res.vector_id: res.rank for res in exact}
        matched = [res for res in materialized if res.vector_id in exact_ids]
        recall = min(1.0, len(matched) / float(request.top_k or 1))
        if matched:
            displacement = mean(
                abs(exact_ids[res.vector_id] - res.rank) for res in matched
            )
        else:
            displacement = float(request.top_k or 1)
        distance_error = 0.0
        if exact:
            exact_scores = {res.vector_id: res.score for res in exact}
            approx_scores = [
                abs(res.score - exact_scores.get(res.vector_id, res.score))
                for res in materialized
            ]
            distance_error = mean(approx_scores) if approx_scores else 0.0
        truncation_ratio = len(materialized) / float(len(exact) or 1)
        index_info = self._index_info.get(artifact.artifact_id, {})
        index_hash = index_info.get("index_hash") if index_info else None
        if index_hash is not None:
            index_hash = str(index_hash)
        return ApproximationReport(
            recall_at_k=recall,
            rank_displacement=displacement,
            distance_error=distance_error,
            algorithm="reference_ann_truncation",
            algorithm_version="v1",
            backend="memory",
            backend_version="reference",
            randomness_sources=self.randomness_sources,
            deterministic_fallback_used=False,
            truncation_ratio=truncation_ratio,
            index_parameters=(("backend", "reference"),),
            query_parameters=self._query_params_metadata(),
            n_candidates=len(materialized),
            random_seed=self._seed_value(),
            candidate_k=getattr(request.nd_settings, "candidate_k", None),
            index_hash=index_hash,
        )

    # ---- internals -----------------------------------------------------

    def _truncate_results(
        self, artifact: ExecutionArtifact, request: ExecutionRequest
    ) -> Iterable[Result]:
        results = list(self.vectors.query(artifact.artifact_id, request))
        if not results:
            return ()
        truncated = results[: max(1, len(results) // 2)]
        return truncated

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


__all__ = ["ReferenceAnnRunner"]
