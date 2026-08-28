# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Diagnostic and configuration commands for the CLI boundary."""

from __future__ import annotations

import sys

import typer

from bijux_canon_index.application.engine import VectorExecutionEngine
from bijux_canon_index.application.surface_services import (
    debug_bundle_payload,
    metrics_payload,
)
from bijux_canon_index.core.errors import BijuxError
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
        _emit(ctx, metrics_payload())
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
        _emit(
            ctx,
            debug_bundle_payload(
                engine=engine,
                redacted_config=_redact_config(config),
                include_provenance=include_provenance,
            ),
        )
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


__all__ = ["register_diagnostic_commands"]
