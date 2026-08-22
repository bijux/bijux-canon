# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Application services for index tuning and benchmark execution."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from statistics import mean
import time
from typing import TypedDict

from bijux_canon_index.application.engine import VectorExecutionEngine
from bijux_canon_index.core.config import ExecutionConfig
from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.errors import ValidationError
from bijux_canon_index.core.execution_intent import ExecutionIntent
from bijux_canon_index.core.execution_mode import ExecutionMode
from bijux_canon_index.core.identity.ids import fingerprint
from bijux_canon_index.core.types import ExecutionRequest, NDSettings, Result
from bijux_canon_index.domain.requests import scoring
from bijux_canon_index.domain.requests.execution_diff import _rank_instability
from bijux_canon_index.interfaces.schemas.requests import IngestRequest
from bijux_canon_index.tooling.benchmarks.dataset import (
    DEFAULT_DIMENSION,
    DEFAULT_QUERY_COUNT,
    DEFAULT_SEED,
    dataset_folder,
    generate_dataset,
    load_dataset,
    save_dataset,
)
from bijux_canon_index.tooling.benchmarks.runner import format_table, run_benchmark


class _AnnParameters(TypedDict):
    m: int
    ef_construction: int
    ef_search: int


class _LatencyMetrics(TypedDict):
    mean: float
    p95: float


class _QualityMetrics(TypedDict):
    overlap_at_k: float
    rank_instability: float


class _AnnTuningResult(TypedDict):
    params: _AnnParameters
    latency_ms: _LatencyMetrics
    quality: _QualityMetrics
    samples: int


def tune_ann(
    *,
    config: ExecutionConfig,
    top_k: int,
    samples: int,
    cache: Path | None,
    dataset_dir: Path | None,
    size: int,
    dimension: int,
    query_count: int,
    seed: int,
    use_existing: bool,
) -> dict[str, object]:
    """Tune admitted ANN parameters and return the Pareto analysis."""
    engine = VectorExecutionEngine(config=config)
    ann_runner = getattr(engine.backend, "ann", None)
    if ann_runner is None:
        raise ValidationError(message="ANN runner required for tuning")
    artifact = engine.stores.ledger.get_artifact(engine.default_artifact_id)
    if artifact is None:
        raise ValidationError(message="No artifact available for tuning")
    vectors = list(engine.stores.vectors.list_vectors())
    queries: list[tuple[float, ...]] = []
    if dataset_dir and not use_existing:
        folder = dataset_folder(dataset_dir, size, dimension, seed)
        if not folder.exists():
            dataset = generate_dataset(
                size=size,
                dimension=dimension,
                query_count=query_count,
                seed=seed,
            )
            save_dataset(dataset, folder)
        dataset = load_dataset(folder)
        engine.ingest(
            IngestRequest(
                documents=dataset.documents,
                vectors=dataset.vectors.tolist(),
            )
        )
        vectors = list(engine.stores.vectors.list_vectors())
        queries = [tuple(query.tolist()) for query in dataset.queries[: max(1, samples)]]
    if not vectors:
        raise ValidationError(message="No vectors available for tuning")
    if not queries:
        queries = [tuple(vector.values) for vector in vectors[: max(1, samples)]]
    cache_key = fingerprint(
        {
            "vector_fingerprint": artifact.vector_fingerprint,
            "metric": artifact.metric,
            "dimension": vectors[0].dimension,
            "runner": ann_runner.__class__.__name__,
            "runner_version": getattr(ann_runner, "__version__", "unknown"),
            "top_k": top_k,
            "samples": samples,
            "dataset": {
                "dir": str(dataset_dir) if dataset_dir else None,
                "size": size,
                "dimension": dimension,
                "query_count": query_count,
                "seed": seed,
                "use_existing": use_existing,
            },
        }
    )
    if cache is not None and cache.exists():
        cached = json.loads(cache.read_text(encoding="utf-8"))
        if cached.get("cache_key") == cache_key:
            return dict(cached["payload"])

    def exact(query: tuple[float, ...]) -> list[Result]:
        scored: list[Result] = []
        for vector in vectors:
            score = scoring.score(artifact.metric, query, tuple(vector.values))
            scored.append(
                Result(
                    request_id="nd-tune",
                    document_id="",
                    chunk_id=vector.chunk_id,
                    vector_id=vector.vector_id,
                    artifact_id=artifact.artifact_id,
                    score=score,
                    rank=0,
                )
            )
        scored.sort(key=scoring.tie_break_key)
        return scored[:top_k]

    exact_cache = {query: exact(query) for query in queries}
    results: list[_AnnTuningResult] = []
    for m_value in (8, 16, 32):
        for ef_construction in (100, 200):
            for ef_search in (50, 100, 200):
                settings = NDSettings(
                    profile=None,
                    m=m_value,
                    ef_construction=ef_construction,
                    ef_search=ef_search,
                    build_on_demand=True,
                )
                ann_runner.build_index(
                    artifact.artifact_id, vectors, artifact.metric, settings
                )
                request = ExecutionRequest(
                    request_id=f"nd-tune-m{m_value}-efc{ef_construction}-efs{ef_search}",
                    text=None,
                    vector=queries[0],
                    top_k=top_k,
                    execution_contract=ExecutionContract.NON_DETERMINISTIC,
                    execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
                    execution_mode=ExecutionMode.BOUNDED,
                    nd_settings=settings,
                )
                latencies: list[float] = []
                overlaps: list[float] = []
                instabilities: list[float] = []
                for query in queries:
                    start = time.perf_counter()
                    ann_results = list(
                        ann_runner.approximate_request(
                            artifact,
                            replace(request, vector=query),
                        )
                    )
                    latencies.append((time.perf_counter() - start) * 1000)
                    exact_results = exact_cache[query]
                    ids_ann = [result.vector_id for result in ann_results]
                    ids_exact = [result.vector_id for result in exact_results]
                    overlap = set(ids_ann) & set(ids_exact)
                    overlaps.append(len(overlap) / float(len(ids_exact) or 1))
                    instabilities.append(_rank_instability(ids_ann, ids_exact, overlap))
                p95 = (
                    sorted(latencies)[int(len(latencies) * 0.95) - 1]
                    if latencies
                    else 0.0
                )
                results.append(
                    {
                        "params": {
                            "m": m_value,
                            "ef_construction": ef_construction,
                            "ef_search": ef_search,
                        },
                        "latency_ms": {
                            "mean": round(mean(latencies), 3) if latencies else 0.0,
                            "p95": round(p95, 3),
                        },
                        "quality": {
                            "overlap_at_k": round(mean(overlaps), 4)
                            if overlaps
                            else 0.0,
                            "rank_instability": round(mean(instabilities), 4)
                            if instabilities
                            else 0.0,
                        },
                        "samples": len(latencies),
                    }
                )

    def dominates(left: _AnnTuningResult, right: _AnnTuningResult) -> bool:
        left_latency = left["latency_ms"]["mean"]
        right_latency = right["latency_ms"]["mean"]
        left_quality = left["quality"]["overlap_at_k"]
        right_quality = right["quality"]["overlap_at_k"]
        return (left_latency <= right_latency and left_quality >= right_quality) and (
            left_latency < right_latency or left_quality > right_quality
        )

    pareto = [
        candidate
        for candidate in results
        if not any(
            dominates(other, candidate) for other in results if other is not candidate
        )
    ]
    recommended = max(
        results,
        key=lambda result: (
            result["quality"]["overlap_at_k"],
            -result["latency_ms"]["mean"],
        ),
    )
    params = recommended["params"]
    payload: dict[str, object] = {
        "grid": results,
        "pareto_frontier": pareto,
        "recommended": recommended,
        "config_snippet": "\n".join(
            [
                "[nd]",
                f"m = {params['m']}",
                f"ef_construction = {params['ef_construction']}",
                f"ef_search = {params['ef_search']}",
                "two_stage = true",
            ]
        ),
    }
    if cache is not None:
        cache.write_text(
            json.dumps({"cache_key": cache_key, "payload": payload}, indent=2),
            encoding="utf-8",
        )
    return payload


def benchmark_index(
    *,
    size: int,
    mode: str,
    backend: str | None,
    vector_store_uri: str | None,
    repeats: int,
    warmup: int,
    seed: int,
    dimension: int,
    query_count: int,
    dataset_dir: Path,
    baseline: Path | None,
    regress_threshold: float,
    overlap_regress_threshold: float,
) -> tuple[dict[str, object], str, bool]:
    """Execute the canonical benchmark and evaluate its optional baseline."""
    folder = dataset_folder(dataset_dir, size, dimension, seed)
    if not folder.exists():
        dataset = generate_dataset(
            size=size,
            dimension=dimension,
            query_count=query_count,
            seed=seed,
        )
        save_dataset(dataset, folder)
    dataset = load_dataset(folder)
    result = run_benchmark(
        documents=dataset.documents,
        vectors=dataset.vectors,
        queries=dataset.queries,
        store_backend=backend,
        store_uri=vector_store_uri,
        mode=mode,
        top_k=5,
        repeats=repeats,
        warmup=warmup,
    )
    table = format_table(result["summary"])
    regressed = False
    if baseline is not None:
        baseline_payload = json.loads(baseline.read_text(encoding="utf-8"))
        base_summary = baseline_payload.get("summary", {})
        if base_summary:
            slowdown = (
                result["summary"]["mean_ms"] / base_summary.get("mean_ms", 1.0)
            ) - 1.0
            regressed = slowdown > regress_threshold
            result["regression"] = {
                "slowdown_pct": slowdown * 100.0,
                "threshold_pct": regress_threshold * 100.0,
                "regressed": regressed,
            }
            if "quality" in result and "quality" in baseline_payload:
                base_quality = baseline_payload.get("quality", {})
                if base_quality:
                    overlap_delta = base_quality.get("overlap_at_k", 1.0) - result[
                        "quality"
                    ].get("overlap_at_k", 1.0)
                    result["regression"]["overlap_drop"] = overlap_delta
                    result["regression"]["overlap_threshold"] = (
                        overlap_regress_threshold
                    )
                    result["regression"]["overlap_regressed"] = (
                        overlap_delta > overlap_regress_threshold
                    )
    return result, table, regressed


__all__ = [
    "DEFAULT_DIMENSION",
    "DEFAULT_QUERY_COUNT",
    "DEFAULT_SEED",
    "benchmark_index",
    "tune_ann",
]
