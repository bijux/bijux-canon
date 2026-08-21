# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Benchmarking and tuning commands for the CLI boundary."""

from __future__ import annotations

from pathlib import Path
import sys

import typer

from bijux_canon_index.application.performance_service import (
    DEFAULT_DIMENSION,
    DEFAULT_QUERY_COUNT,
    DEFAULT_SEED,
    benchmark_index,
    tune_ann,
)
from bijux_canon_index.core.errors import BijuxError
from bijux_canon_index.interfaces.cli.configuration import build_config as _build_config
from bijux_canon_index.interfaces.cli.options import (
    ND_TUNE_CACHE_OPTION,
    ND_TUNE_DATASET_DIR_OPTION,
)
from bijux_canon_index.interfaces.cli.rendering import emit as _emit
from bijux_canon_index.interfaces.errors import (
    is_refusal,
    refusal_payload,
    to_cli_exit,
)
from bijux_canon_index.interfaces.errors.reporting import record_failure


def register_performance_commands(app: typer.Typer, nd_app: typer.Typer) -> None:
    """Register performance commands."""
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
    """Handle ND tune."""
    try:
        payload = tune_ann(
            config=_build_config(vector_store=vector_store, vector_store_uri=uri),
            top_k=top_k,
            samples=samples,
            cache=cache,
            dataset_dir=dataset_dir,
            size=size,
            dimension=dimension,
            query_count=query_count,
            seed=seed,
            use_existing=use_existing,
        )
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
    """Handle bench."""
    try:
        if store not in {"memory", "vdb"}:
            typer.echo("store must be memory|vdb")
            sys.exit(1)
        backend = vector_store or "faiss" if store == "vdb" else None
        result, table, regressed = benchmark_index(
            size=size,
            mode=mode,
            backend=backend,
            vector_store_uri=vector_store_uri,
            repeats=repeats,
            warmup=warmup,
            seed=seed,
            dimension=dimension,
            query_count=query_count,
            dataset_dir=dataset_dir,
            baseline=baseline,
            regress_threshold=regress_threshold,
            overlap_regress_threshold=overlap_regress_threshold,
        )
        if regressed and fail_on_regression:
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
