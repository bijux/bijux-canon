# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
import math

from bijux_vex.contracts.resources import VectorSource
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import InvariantError, ValidationError
from bijux_vex.core.runtime.vector_execution import RandomnessProfile, VectorExecution
from bijux_vex.core.types import ExecutionArtifact, ExecutionRequest, Result, Vector
from bijux_vex.domain.execution_algorithms.base import (
    VectorExecutionAlgorithm,
    register_algorithm,
)
from bijux_vex.domain.execution_requests import scoring
from bijux_vex.infra.adapters.ann_base import AnnExecutionRequestRunner


class ExactVectorExecutionAlgorithm(VectorExecutionAlgorithm):
    name = "exact_vector_execution"
    supported_contracts = {ExecutionContract.DETERMINISTIC}

    def plan(
        self,
        artifact: ExecutionArtifact,
        request: ExecutionRequest,
        backend_id: str,
    ) -> VectorExecution:
        if artifact.execution_contract is not request.execution_contract:
            raise InvariantError(
                message="Execution contract does not match artifact execution contract",
                invariant_id="INV-010",
            )
        return VectorExecution(
            request=request,
            contract=request.execution_contract,
            backend_id=backend_id,
            algorithm=self.name,
            parameters=(("metric", artifact.metric), ("top_k", request.top_k)),
            randomness=None,
        )

    def execute(
        self,
        execution: VectorExecution,
        artifact: ExecutionArtifact,
        vectors: VectorSource,
    ) -> Iterable[Result]:
        request = execution.request
        if request.vector is None:
            raise ValidationError(
                message="execution vector required", invariant_id="INV-020"
            )
        query_vec = request.vector
        scored: list[Result] = []
        for vector in vectors.list_vectors():
            vector = _ensure_tuple(vector)
            if len(query_vec) != vector.dimension:
                continue
            score = scoring.score(artifact.metric, query_vec, vector.values)
            chunk = vectors.get_chunk(vector.chunk_id)
            document_id = chunk.document_id if chunk else ""
            scored.append(
                Result(
                    request_id=request.request_id,
                    document_id=document_id,
                    chunk_id=vector.chunk_id,
                    vector_id=vector.vector_id,
                    artifact_id=artifact.artifact_id,
                    score=score,
                    rank=0,
                )
            )
        scored.sort(key=scoring.tie_break_key)
        limited = scored[: request.top_k]
        for idx, res in enumerate(limited, start=1):
            limited[idx - 1] = Result(
                request_id=res.request_id,
                document_id=res.document_id,
                chunk_id=res.chunk_id,
                vector_id=res.vector_id,
                artifact_id=res.artifact_id,
                score=res.score,
                rank=idx,
            )
        return limited


class ApproximateAnnAlgorithm(VectorExecutionAlgorithm):
    name = "ann_approximate"
    supported_contracts = {ExecutionContract.NON_DETERMINISTIC}

    def __init__(self, runner: AnnExecutionRequestRunner):
        self.runner = runner

    def plan(
        self,
        artifact: ExecutionArtifact,
        request: ExecutionRequest,
        backend_id: str,
    ) -> VectorExecution:
        if artifact.execution_contract is not request.execution_contract:
            raise InvariantError(
                message="Execution contract does not match artifact execution contract",
                invariant_id="INV-010",
            )
        self.runner.ensure_contract(artifact)
        surface = RandomnessProfile(
            sources=tuple(self.runner.randomness_sources),
            bounded=False,
        )
        return VectorExecution(
            request=request,
            contract=request.execution_contract,
            backend_id=backend_id,
            algorithm=self.name,
            parameters=(("top_k", request.top_k),),
            randomness=surface,
        )

    def execute(
        self,
        execution: VectorExecution,
        artifact: ExecutionArtifact,
        vectors: VectorSource,
    ) -> Iterable[Result]:
        if getattr(self.runner, "force_fallback", False):
            return self.runner.deterministic_fallback(
                artifact.artifact_id, execution.request
            )
        self.runner.set_randomness_profile(execution.randomness)
        request = execution.request
        nd_settings = request.nd_settings
        if request.vector is None:
            raise ValidationError(
                message="execution vector required", invariant_id="INV-020"
            )
        candidate_k = request.top_k
        if nd_settings and nd_settings.candidate_k:
            candidate_k = max(candidate_k, int(nd_settings.candidate_k))
        if nd_settings and nd_settings.max_candidates:
            candidate_k = min(candidate_k, int(nd_settings.max_candidates))
        if candidate_k != request.top_k:
            request = replace(request, top_k=candidate_k)
        candidates = list(self.runner.approximate_request(artifact, request))
        if not candidates:
            return ()
        need_rescore = True
        if nd_settings and nd_settings.two_stage is False:
            if candidate_k == execution.request.top_k:
                need_rescore = False
            if nd_settings.normalize_vectors or nd_settings.normalize_query:
                need_rescore = True
            if nd_settings.diversity_lambda is not None:
                need_rescore = True
        if not need_rescore:
            candidates.sort(key=scoring.tie_break_key)
            limited = candidates[: execution.request.top_k]
            for idx, res in enumerate(limited, start=1):
                limited[idx - 1] = Result(
                    request_id=res.request_id,
                    document_id=res.document_id,
                    chunk_id=res.chunk_id,
                    vector_id=res.vector_id,
                    artifact_id=res.artifact_id,
                    score=res.score,
                    rank=idx,
                )
            return limited
        query_vec = execution.request.vector
        if query_vec is None:
            raise ValidationError(
                message="execution vector required", invariant_id="INV-020"
            )
        qvec = _maybe_normalize(
            query_vec, nd_settings.normalize_query if nd_settings else False
        )
        rescored: list[Result] = []
        for res in candidates:
            vec = vectors.get_vector(res.vector_id)
            if vec is None:
                continue
            tvec = _ensure_tuple(vec).values
            tvec = _maybe_normalize(
                tvec, nd_settings.normalize_vectors if nd_settings else False
            )
            score = scoring.score(artifact.metric, qvec, tvec)
            chunk = vectors.get_chunk(res.chunk_id)
            document_id = chunk.document_id if chunk else res.document_id
            rescored.append(
                Result(
                    request_id=execution.request.request_id,
                    document_id=document_id,
                    chunk_id=res.chunk_id,
                    vector_id=res.vector_id,
                    artifact_id=res.artifact_id,
                    score=score,
                    rank=0,
                )
            )
        rescored.sort(key=scoring.tie_break_key)
        if nd_settings and nd_settings.diversity_lambda is not None:
            rescored = _mmr_rerank(
                rescored,
                vectors,
                qvec,
                artifact.metric,
                float(nd_settings.diversity_lambda),
                execution.request.top_k,
            )
        limited = rescored[: execution.request.top_k]
        for idx, res in enumerate(limited, start=1):
            limited[idx - 1] = Result(
                request_id=res.request_id,
                document_id=res.document_id,
                chunk_id=res.chunk_id,
                vector_id=res.vector_id,
                artifact_id=res.artifact_id,
                score=res.score,
                rank=idx,
            )
        return limited


def build_ann_algorithm(runner: AnnExecutionRequestRunner) -> ApproximateAnnAlgorithm:
    algo = ApproximateAnnAlgorithm(runner)
    register_algorithm(algo)
    return algo


def register_algorithms() -> None:
    register_algorithm(ExactVectorExecutionAlgorithm())


def _ensure_tuple(vector: Vector) -> Vector:
    if isinstance(vector.values, tuple):
        return vector
    return Vector(
        vector_id=vector.vector_id,
        chunk_id=vector.chunk_id,
        values=tuple(vector.values),
        dimension=vector.dimension,
        model=vector.model,
    )


def _maybe_normalize(vec: tuple[float, ...], enabled: bool) -> tuple[float, ...]:
    if not enabled:
        return vec
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return tuple(v / norm for v in vec)


def _mmr_rerank(
    results: list[Result],
    vectors: VectorSource,
    query_vec: tuple[float, ...],
    metric: str,
    diversity_lambda: float,
    k: int,
) -> list[Result]:
    if not results:
        return results
    diversity_lambda = min(1.0, max(0.0, diversity_lambda))
    selected: list[Result] = []
    candidates = results[:]
    query_sim: dict[str, float] = {}
    for res in candidates:
        vec = vectors.get_vector(res.vector_id)
        if vec is None:
            continue
        v = _ensure_tuple(vec).values
        query_sim[res.vector_id] = _cosine_similarity(query_vec, v)
    while candidates and len(selected) < k:
        best = None
        best_score = None
        for res in candidates:
            sim_q = query_sim.get(res.vector_id, 0.0)
            sim_selected = 0.0
            for chosen in selected:
                chosen_vec = vectors.get_vector(chosen.vector_id)
                if chosen_vec is None:
                    continue
                sim_selected = max(
                    sim_selected,
                    _cosine_similarity(query_vec, _ensure_tuple(chosen_vec).values),
                )
            mmr = diversity_lambda * sim_q - (1.0 - diversity_lambda) * sim_selected
            if best_score is None or mmr > best_score:
                best_score = mmr
                best = res
        if best is None:
            break
        selected.append(best)
        candidates = [c for c in candidates if c.vector_id != best.vector_id]
    return selected + candidates


def _cosine_similarity(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    denom = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(x * x for x in b))
    if denom == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b, strict=True)) / denom


register_algorithms()

__all__ = [
    "ExactVectorExecutionAlgorithm",
    "ApproximateAnnAlgorithm",
    "build_ann_algorithm",
]
