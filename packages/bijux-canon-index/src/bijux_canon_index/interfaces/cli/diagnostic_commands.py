# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Diagnostic and configuration commands for the CLI boundary."""

from __future__ import annotations

import sys

import typer

from bijux_canon_index.application.engine import VectorExecutionEngine
from bijux_canon_index.core.errors import BijuxError
from bijux_canon_index.infra.metrics import METRICS
from bijux_canon_index.interfaces.cli.configuration import (
    build_config as _build_config,
)
from bijux_canon_index.interfaces.cli.configuration import (
    load_config as _load_config,
)
from bijux_canon_index.interfaces.cli.rendering import (
    emit as _emit,
)
from bijux_canon_index.interfaces.cli.rendering import (
    redact_config as _redact_config,
)
from bijux_canon_index.interfaces.errors import (
    is_refusal,
    refusal_payload,
    to_cli_exit,
)
from bijux_canon_index.interfaces.errors.reporting import record_failure


def register_diagnostic_commands(app: typer.Typer, config_app: typer.Typer) -> None:
    """Register diagnostic commands."""
    config_app.command("show")(config_show)
    app.command("metrics")(metrics_snapshot)
    app.command("debug-bundle")(debug_bundle)


def config_show(ctx: typer.Context) -> None:
    """Handle config show."""
    try:
        config = _load_config(ctx.obj.config_path) if ctx.obj else None
        _emit(ctx, _redact_config(config))
    except Exception:  # pragma: no cover
        sys.exit(1)


def metrics_snapshot(ctx: typer.Context) -> None:
    """Handle metrics snapshot."""
    try:
        snapshot = METRICS.snapshot()
        _emit(
            ctx,
            {"counters": snapshot.counters, "timers_ms": snapshot.timers_ms},
        )
    except Exception:  # pragma: no cover
        sys.exit(1)


def debug_bundle(
    ctx: typer.Context,
    include_provenance: bool = typer.Option(False, "--include-provenance"),
    vector_store: str | None = typer.Option(None, "--vector-store"),
    vector_store_uri: str | None = typer.Option(None, "--vector-store-uri"),
) -> None:
    """Handle debug bundle."""
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
                "artifacts": [artifact.artifact_id for artifact in artifacts],
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


__all__ = ["register_diagnostic_commands"]
