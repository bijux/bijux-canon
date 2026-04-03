# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""CLI entrypoint that composes command modules at the interface boundary."""

from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
from statistics import mean
import sys
import time
from typing import no_type_check
import zipfile

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
from bijux_canon_index.infra.logging import enable_trace
from bijux_canon_index.infra.metrics import METRICS
from bijux_canon_index.infra.run_store import RunStore
from bijux_canon_index.interfaces.cli.configuration import (
    build_config as _build_config,
    load_config as _load_config,
)
from bijux_canon_index.interfaces.cli.execution_commands import (
    register_execution_commands,
)
from bijux_canon_index.interfaces.cli.options import (
    ND_TUNE_CACHE_OPTION,
    ND_TUNE_DATASET_DIR_OPTION,
)
from bijux_canon_index.interfaces.cli.rendering import (
    OutputOptions,
    emit as _emit,
    redact_config as _redact_config,
)
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

app = typer.Typer(add_completion=False)
vdb_app = typer.Typer(add_completion=False, help="Vector DB utilities")
app.add_typer(vdb_app, name="vdb")
nd_app = typer.Typer(add_completion=False, help="ND utilities")
app.add_typer(nd_app, name="nd")
config_app = typer.Typer(add_completion=False, help="Configuration utilities")
app.add_typer(config_app, name="config")
artifact_app = typer.Typer(add_completion=False, help="Artifact bundle utilities")
app.add_typer(artifact_app, name="artifact")
register_execution_commands(app)


@app.callback()
@no_type_check
def _main_callback(
    ctx: typer.Context,
    fmt: str | None = typer.Option(
        None, "--format", help="Output format: json|table (default: json)"
    ),
    output: Path | None = typer.Option(  # noqa: B008
        None, "--output", help="Write output to a file"
    ),
    config: Path | None = typer.Option(  # noqa: B008
        None, "--config", help="Load configuration from a TOML/YAML file"
    ),
    trace: bool = typer.Option(False, "--trace", help="Emit trace metadata"),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress non-error output"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output"),
) -> None:
    if trace:
        enable_trace()
    if no_color:
        os.environ["RICH_NO_COLOR"] = "1"
        os.environ["TYPER_COLOR"] = "0"
    ctx.obj = OutputOptions(
        fmt=fmt,
        output=output,
        config_path=config,
        trace=trace,
        quiet=quiet,
        no_color=no_color,
    )


@vdb_app.command("status")
@no_type_check
def vdb_status(
    ctx: typer.Context,
    vector_store: str = typer.Option(..., "--vector-store"),
    uri: str | None = typer.Option(None, "--uri"),
) -> None:
    try:
        engine = VectorExecutionEngine(
            config=_build_config(vector_store=vector_store, vector_store_uri=uri)
        )
        adapter = engine.vector_store_resolution.adapter
        status = {
            "backend": engine.vector_store_resolution.descriptor.name,
            "reachable": True,
            "version": engine.vector_store_resolution.descriptor.version,
            "uri_redacted": engine.vector_store_resolution.uri_redacted,
        }
        if hasattr(adapter, "status"):
            status.update(adapter.status())
        ann_runner = getattr(engine.backend, "ann", None)
        if ann_runner is not None and hasattr(ann_runner, "index_info"):
            status["ann_index"] = ann_runner.index_info(engine.default_artifact_id)
        _emit(ctx, status)
    except BijuxError as exc:
        record_failure(exc)
        payload = {"backend": vector_store, "reachable": False}
        if is_refusal(exc):
            payload["error"] = refusal_payload(exc)
        else:
            payload["error"] = {"message": str(exc)}
        _emit(ctx, payload)
    except Exception:  # pragma: no cover
        sys.exit(1)


@vdb_app.command("rebuild")
@no_type_check
def vdb_rebuild(
    ctx: typer.Context,
    vector_store: str = typer.Option(..., "--vector-store"),
    uri: str | None = typer.Option(None, "--uri"),
    mode: str = typer.Option("exact", "--mode", help="exact|ann"),
) -> None:
    try:
        engine = VectorExecutionEngine(
            config=_build_config(vector_store=vector_store, vector_store_uri=uri)
        )
        index_type = "exact" if mode == "exact" else "ann"
        if index_type == "ann":
            ann_runner = getattr(engine.backend, "ann", None)
            if ann_runner is None:
                raise ValidationError(
                    message="Selected backend does not support ANN rebuild"
                )
            artifact = engine.stores.ledger.get_artifact(engine.default_artifact_id)
            if artifact is None:
                raise ValidationError(message="No artifact available for ANN rebuild")
            vectors = list(engine.stores.vectors.list_vectors())
            index_info = ann_runner.build_index(
                artifact.artifact_id, vectors, artifact.metric, None
            )
            index_hash = index_info.get("index_hash") if index_info else None
            extra = (("ann_index_info", json.dumps(index_info, sort_keys=True)),)
            if index_hash:
                extra = extra + (("ann_index_hash", str(index_hash)),)
            updated = replace(
                artifact,
                build_params=artifact.build_params + extra,
                index_state="ready",
            )
            with engine._tx() as tx:
                engine.stores.ledger.put_artifact(tx, updated)
            _emit(ctx, {"status": "rebuilt", "ann_index": index_info})
            return
        adapter = engine.vector_store_resolution.adapter
        if not hasattr(adapter, "rebuild"):
            raise ValidationError(
                message="Selected vector store does not support rebuild"
            )
        status = adapter.rebuild(index_type=index_type)
        _emit(ctx, status)
    except BijuxError as exc:
        record_failure(exc)
        payload = {"backend": vector_store, "reachable": False}
        if is_refusal(exc):
            payload["error"] = refusal_payload(exc)
        else:
            payload["error"] = {"message": str(exc)}
        _emit(ctx, payload)
    except Exception:  # pragma: no cover
        sys.exit(1)


@vdb_app.command("compact")
@no_type_check
def vdb_compact(
    ctx: typer.Context,
    vector_store: str = typer.Option(..., "--vector-store"),
    uri: str | None = typer.Option(None, "--uri"),
    mode: str = typer.Option("ann", "--mode", help="exact|ann"),
) -> None:
    try:
        engine = VectorExecutionEngine(
            config=_build_config(vector_store=vector_store, vector_store_uri=uri)
        )
        index_type = "exact" if mode == "exact" else "ann"
        if index_type == "ann":
            ann_runner = getattr(engine.backend, "ann", None)
            if ann_runner is None or not getattr(
                ann_runner, "supports_compaction", False
            ):
                raise ValidationError(
                    message="Selected backend does not support ANN compaction"
                )
            artifact = engine.stores.ledger.get_artifact(engine.default_artifact_id)
            if artifact is None:
                raise ValidationError(
                    message="No artifact available for ANN compaction"
                )
            vectors = list(engine.stores.vectors.list_vectors())
            ann_runner.compact(artifact.artifact_id, vectors, artifact.metric)
            _emit(ctx, {"status": "compacted", "backend": vector_store})
            return
        adapter = engine.vector_store_resolution.adapter
        if not hasattr(adapter, "compact"):
            raise ValidationError(
                message="Selected vector store does not support compaction"
            )
        status = adapter.compact(index_type=index_type)
        _emit(ctx, status)
    except BijuxError as exc:
        record_failure(exc)
        payload = {"backend": vector_store, "reachable": False}
        if is_refusal(exc):
            payload["error"] = refusal_payload(exc)
        else:
            payload["error"] = {"message": str(exc)}
        _emit(ctx, payload)
    except Exception:  # pragma: no cover
        sys.exit(1)


@nd_app.command("tune")
@no_type_check
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
            folder = dataset_folder(Path(dataset_dir), size, dimension, seed)
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
            queries = [tuple(q.tolist()) for q in dataset.queries[: max(1, samples)]]
        if not vectors:
            raise ValidationError(message="No vectors available for tuning")
        if not queries:
            queries = [tuple(v.values) for v in vectors[: max(1, samples)]]
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
        for m_val in grid["m"]:
            for efc in grid["ef_construction"]:
                for efs in grid["ef_search"]:
                    nd_settings = NDSettings(
                        profile=None,
                        m=m_val,
                        ef_construction=efc,
                        ef_search=efs,
                        build_on_demand=True,
                    )
                    ann_runner.build_index(
                        artifact.artifact_id, vectors, artifact.metric, nd_settings
                    )
                    request = ExecutionRequest(
                        request_id=f"nd-tune-m{m_val}-efc{efc}-efs{efs}",
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
                        ids_ann = [r.vector_id for r in ann_results]
                        ids_exact = [r.vector_id for r in exact_results]
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
                    result = {
                        "params": {
                            "m": m_val,
                            "ef_construction": efc,
                            "ef_search": efs,
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
                    results.append(result)

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
            key=lambda r: (r["quality"]["overlap_at_k"], -r["latency_ms"]["mean"]),
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


@artifact_app.command("pack")
@no_type_check
def artifact_pack(
    ctx: typer.Context,
    run_id: str = typer.Argument(...),
    out: Path = typer.Option(Path("bundle.zip"), "--out"),  # noqa: B008
    include_vectors: bool = typer.Option(False, "--include-vectors"),
) -> None:
    try:
        run = RunStore().load(run_id)
        base_config = _load_config(ctx.obj.config_path) if ctx.obj else None
        config_payload = _redact_config(base_config)
        engine = VectorExecutionEngine()
        vectors_payload: dict[str, object] = {}
        if include_vectors:
            vectors_payload["vectors"] = []
            for vid in run.result.get("results", []) if run.result else []:
                vec = engine.stores.vectors.get_vector(vid)
                if vec:
                    vectors_payload["vectors"].append(
                        {"vector_id": vid, "values": list(vec.values)}
                    )
        vector_hashes = []
        for vid in run.result.get("results", []) if run.result else []:
            vec = engine.stores.vectors.get_vector(vid)
            if vec:
                vector_hashes.append(
                    {"vector_id": vid, "hash": fingerprint(vec.values)}
                )
        bundle = {
            "metadata": run.metadata,
            "result": run.result or {},
            "config": config_payload,
            "vector_hashes": vector_hashes,
        }
        with zipfile.ZipFile(out, "w") as zf:
            zf.writestr("metadata.json", json.dumps(bundle["metadata"], indent=2))
            zf.writestr("result.json", json.dumps(bundle["result"], indent=2))
            zf.writestr("config.json", json.dumps(bundle["config"], indent=2))
            zf.writestr(
                "vector_hashes.json", json.dumps(bundle["vector_hashes"], indent=2)
            )
            if include_vectors:
                zf.writestr("vectors.json", json.dumps(vectors_payload, indent=2))
        _emit(ctx, {"status": "packed", "bundle": str(out)})
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


@artifact_app.command("unpack")
@no_type_check
def artifact_unpack(
    ctx: typer.Context,
    bundle: Path = typer.Argument(...),  # noqa: B008
    out_dir: Path = typer.Option(Path("bundle_out"), "--out-dir"),  # noqa: B008
) -> None:
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(bundle, "r") as zf:
            zf.extractall(out_dir)
        _emit(ctx, {"status": "unpacked", "path": str(out_dir)})
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


@app.command()
@no_type_check
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
        backend = None
        if store == "vdb":
            backend = vector_store or "faiss"
        base = dataset_dir
        folder = dataset_folder(base, size, dimension, seed)
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


@config_app.command("show")
@no_type_check
def config_show(ctx: typer.Context) -> None:
    try:
        config = _load_config(ctx.obj.config_path) if ctx.obj else None
        _emit(ctx, _redact_config(config))
    except Exception:  # pragma: no cover
        sys.exit(1)


@app.command("metrics")
@no_type_check
def metrics_snapshot(ctx: typer.Context) -> None:
    try:
        snapshot = METRICS.snapshot()
        _emit(
            ctx,
            {"counters": snapshot.counters, "timers_ms": snapshot.timers_ms},
        )
    except Exception:  # pragma: no cover
        sys.exit(1)


@app.command("debug-bundle")
@no_type_check
def debug_bundle(
    ctx: typer.Context,
    include_provenance: bool = typer.Option(False, "--include-provenance"),
    vector_store: str | None = typer.Option(None, "--vector-store"),
    vector_store_uri: str | None = typer.Option(None, "--vector-store-uri"),
) -> None:
    try:
        base_config = _load_config(ctx.obj.config_path) if ctx.obj else None
        config = _build_config(
            vector_store=vector_store,
            vector_store_uri=vector_store_uri,
            base_config=base_config,
        )
        engine = VectorExecutionEngine(config=config)
        status = {
            "backend": engine.vector_store_resolution.descriptor.name,
            "reachable": True,
            "version": engine.vector_store_resolution.descriptor.version,
            "uri_redacted": engine.vector_store_resolution.uri_redacted,
        }
        adapter = engine.vector_store_resolution.adapter
        if hasattr(adapter, "status"):
            status.update(adapter.status())
        bundle: dict[str, object] = {
            "config": _redact_config(config),
            "capabilities": engine.capabilities(),
            "vector_store_status": status,
            "metrics": METRICS.snapshot().__dict__,
        }
        if include_provenance:
            artifacts = tuple(engine.stores.ledger.list_artifacts())
            latest_exec: dict[str, str] = {}
            for artifact in artifacts:
                stored = engine.stores.ledger.latest_execution_result(
                    artifact.artifact_id
                )
                if stored is not None:
                    latest_exec[artifact.artifact_id] = stored.execution_id
            bundle["provenance"] = {
                "artifacts": [a.artifact_id for a in artifacts],
                "latest_execution_ids": latest_exec,
            }
        _emit(ctx, bundle)
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


if __name__ == "__main__":
    app()
