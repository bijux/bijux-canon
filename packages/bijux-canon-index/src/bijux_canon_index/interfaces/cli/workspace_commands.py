# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Workspace and inventory commands for the CLI boundary."""

from __future__ import annotations

from pathlib import Path
import sys

import typer

from bijux_canon_index.application.engine import VectorExecutionEngine
from bijux_canon_index.core.errors import ValidationError
from bijux_canon_index.infra.run_store import RunStore
from bijux_canon_index.interfaces.cli.configuration import (
    build_config as _build_config,
)
from bijux_canon_index.interfaces.cli.configuration import (
    load_config as _load_config,
)
from bijux_canon_index.interfaces.cli.rendering import emit as _emit
from bijux_canon_index.interfaces.cli.workspace_setup import initialize_workspace


def list_artifacts(
    ctx: typer.Context,
    limit: int | None = typer.Option(None, "--limit"),
    offset: int = typer.Option(0, "--offset"),
) -> None:
    _emit(ctx, VectorExecutionEngine().list_artifacts(limit=limit, offset=offset))


def list_runs(
    ctx: typer.Context,
    limit: int | None = typer.Option(None, "--limit"),
    offset: int = typer.Option(0, "--offset"),
) -> None:
    runs = RunStore().list_runs(limit=limit, offset=offset)
    _emit(ctx, {"runs": runs})


def init(
    ctx: typer.Context,
    config_path: Path = typer.Option(  # noqa: B008
        Path("bijux_canon_index.toml"), "--config-path"
    ),
    force: bool = typer.Option(False, "--force"),
) -> None:
    try:
        _emit(ctx, initialize_workspace(config_path, force=force))
    except ValidationError as exc:
        typer.echo(str(exc))
        sys.exit(1)


def capabilities(ctx: typer.Context) -> None:
    _emit(ctx, VectorExecutionEngine().capabilities())


def audit(
    ctx: typer.Context,
    vector_store: str | None = typer.Option(None, "--vector-store"),
    vector_store_uri: str | None = typer.Option(None, "--vector-store-uri"),
) -> None:
    base_config = _load_config(ctx.obj.config_path) if ctx.obj else None
    config = _build_config(
        vector_store=vector_store,
        vector_store_uri=vector_store_uri,
        base_config=base_config,
    )
    engine = VectorExecutionEngine(config=config)
    caps = engine.capabilities()
    nd_caps = caps.get("ann", {})
    payload = {
        "determinism_guarantees": {
            "exact": "bit-identical when deterministic contract is used",
            "enforced": True,
        },
        "nd_guarantees": {
            "runner": nd_caps.get("default_runner"),
            "supports_seed": nd_caps.get("supports_seed"),
            "quality_metrics_required": True,
            "replay_strict": True,
        },
        "backend_trust": {
            "vector_store": caps.get("vector_store", {}).get("selected"),
            "backend": caps.get("execution", {}).get("backend"),
        },
        "known_limitations": (
            "ND quality is bounded by ANN candidate quality",
            "Benchmarks require explicit baselines on target hardware",
        ),
    }
    _emit(ctx, payload)


__all__ = ["audit", "capabilities", "init", "list_artifacts", "list_runs"]
