# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Benchmarking and tuning commands for the CLI boundary."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from statistics import mean
import sys
import time

import typer

from bijux_canon_index.application.engine import VectorExecutionEngine
from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.errors import BijuxError, ValidationError
from bijux_canon_index.core.execution_intent import ExecutionIntent
from bijux_canon_index.core.execution_mode import ExecutionMode
from bijux_canon_index.core.identity.ids import fingerprint
from bijux_canon_index.core.types import ExecutionRequest, NDSettings, Result
from bijux_canon_index.domain.requests import scoring
from bijux_canon_index.domain.requests.execution_diff import _rank_instability
from bijux_canon_index.interfaces.cli.configuration import build_config as _build_config
from bijux_canon_index.interfaces.cli.options import (
    ND_TUNE_CACHE_OPTION,
    ND_TUNE_DATASET_DIR_OPTION,
)
from bijux_canon_index.interfaces.cli.rendering import emit as _emit
from bijux_canon_index.interfaces.errors import (
    is_refusal,
    record_failure,
    refusal_payload,
    to_cli_exit,
)
from bijux_canon_index.interfaces.schemas.models import IngestRequest
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


def register_performance_commands(app: typer.Typer, nd_app: typer.Typer) -> None:
    nd_app.command("tune")(nd_tune)
    app.command()(bench)


def nd_tune(
    ctx: typer.Context,
    vector_store: str = typer.Option("memory", "--vector-store"),
    uri: str | None = typer.Option(None, "--uri"),
    top_k: int = typer.Option(10, "--top-k"),
    samples: int = typer.Option(10, "--samples"),
    cache: Path | None = ND_TUNE_CACHE_OPTION,
    dataset_dir: Path | None = ND_TUNE_DATASET_DIR_OPTION,
    size: int = typer.Option(1000, "--size"),
    dimension: int = typer.Option(DEFAULT_DIMENSION, "--dimension"),
    query_count: int = typer.Option(DEFAULT_QUERY_COUNT, "--query-count"),
    seed: int = typer.Option(DEFAULT_SEED, "--seed"),
    use_existing: bool = typer.Option(
        False,
        "--use-existing",
        help="Use existing store vectors instead of loading dataset",
    ),
) -> None:
    try:
        engine = VectorExecutionEngine(
            config=_build_config(vector_store=vector_store, vector_store_uri=uri)
        )
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
        dim = vectors[0].dimension
        cache_key = fingerprint(
            {
                "vector_fingerprint": artifact.vector_fingerprint,
                "metric": artifact.metric,
                "dimension": dim,
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
                _emit(ctx, cached["payload"])
                return

        def _exact(query: tuple[float, ...]) -> list[Result]:
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

        exact_cache = {query: _exact(query) for query in queries}
        grid = {
            "m": [8, 16, 32],
            "ef_construction": [100, 200],
            "ef_search": [50, 100, 200],
        }
        results: list[dict[str, object]] = []
        for m_value in grid["m"]:
            for ef_construction in grid["ef_construction"]:
                for ef_search in grid["ef_search"]:
                    nd_settings = NDSettings(
                        profile=None,
                        m=m_value,
                        ef_construction=ef_construction,
                        ef_search=ef_search,
                        build_on_demand=True,
                    )
                    ann_runner.build_index(
                        artifact.artifact_id, vectors, artifact.metric, nd_settings
                    )
                    request = ExecutionRequest(
                        request_id=(
                            "nd-tune-"
                            f"m{m_value}-efc{ef_construction}-efs{ef_search}"
                        ),
                        text=None,
                        vector=queries[0],
                        top_k=top_k,
                        execution_contract=ExecutionContract.NON_DETERMINISTIC,
                        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
                        execution_mode=ExecutionMode.BOUNDED,
                        nd_settings=nd_settings,
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
                        instabilities.append(
                            _rank_instability(ids_ann, ids_exact, overlap)
                        )
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
                                "mean": round(mean(latencies), 3)
                                if latencies
                                else 0.0,
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

        def _dominates(a: dict[str, object], b: dict[str, object]) -> bool:
            a_lat = a["latency_ms"]["mean"]
            b_lat = b["latency_ms"]["mean"]
            a_qual = a["quality"]["overlap_at_k"]
            b_qual = b["quality"]["overlap_at_k"]
            return (a_lat <= b_lat and a_qual >= b_qual) and (
                a_lat < b_lat or a_qual > b_qual
            )

        pareto = []
        for candidate in results:
            if any(
                _dominates(other, candidate)
                for other in results
                if other is not candidate
            ):
                continue
            pareto.append(candidate)

        recommended = max(
            results,
            key=lambda result: (
                result["quality"]["overlap_at_k"],
                -result["latency_ms"]["mean"],
            ),
        )
        params = recommended["params"]
        config_snippet = "\n".join(
            [
                "[nd]",
                f"m = {params['m']}",
                f"ef_construction = {params['ef_construction']}",
                f"ef_search = {params['ef_search']}",
                "two_stage = true",
            ]
        )
        payload = {
            "grid": results,
            "pareto_frontier": pareto,
            "recommended": recommended,
            "config_snippet": config_snippet,
        }
        if cache is not None:
            cache_payload = {"cache_key": cache_key, "payload": payload}
            cache.write_text(json.dumps(cache_payload, indent=2), encoding="utf-8")
        _emit(ctx, payload)
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


def bench(
    ctx: typer.Context,
    size: int = typer.Option(1000, "--size", help="Dataset size (1k/10k/100k)"),
    mode: str = typer.Option("exact", "--mode", help="exact|ann"),
    store: str = typer.Option("memory", "--store", help="memory|vdb"),
    vector_store: str | None = typer.Option(None, "--vector-store"),
    vector_store_uri: str | None = typer.Option(None, "--vector-store-uri"),
    repeats: int = typer.Option(3, "--repeats"),
    warmup: int = typer.Option(1, "--warmup"),
    seed: int = typer.Option(DEFAULT_SEED, "--seed"),
    dimension: int = typer.Option(DEFAULT_DIMENSION, "--dimension"),
    query_count: int = typer.Option(DEFAULT_QUERY_COUNT, "--query-count"),
    dataset_dir: Path = typer.Option(  # noqa: B008
        Path("benchmarks/artifacts"), "--dataset-dir"
    ),
    baseline: Path | None = typer.Option(None, "--baseline"),  # noqa: B008
    fail_on_regression: bool = typer.Option(False, "--fail-on-regression"),
    regress_threshold: float = typer.Option(0.2, "--regress-threshold"),
    overlap_regress_threshold: float = typer.Option(
        0.05, "--overlap-regress-threshold"
    ),
) -> None:
    try:
        if store not in {"memory", "vdb"}:
            typer.echo("store must be memory|vdb")
            sys.exit(1)
        backend = vector_store or "faiss" if store == "vdb" else None
        folder = dataset_folder(dataset_dir, size, dimension, seed)
        if not folder.exists():
            dataset = generate_dataset(
                size=size, dimension=dimension, query_count=query_count, seed=seed
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
        if baseline:
            baseline_payload = json.loads(baseline.read_text(encoding="utf-8"))
            base_summary = baseline_payload.get("summary", {})
            if base_summary:
                slowdown = (
                    result["summary"]["mean_ms"] / base_summary.get("mean_ms", 1.0)
                ) - 1.0
                result["regression"] = {
                    "slowdown_pct": slowdown * 100.0,
                    "threshold_pct": regress_threshold * 100.0,
                    "regressed": slowdown > regress_threshold,
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
                if slowdown > regress_threshold and fail_on_regression:
                    _emit(ctx, result, table=table)
                    sys.exit(2)
        _emit(ctx, result, table=table)
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


__all__ = ["register_performance_commands"]
