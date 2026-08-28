# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Artifact bundle commands for the CLI boundary."""

from __future__ import annotations

from pathlib import Path
import sys

import typer

from bijux_canon_index.application.surface_services import (
    pack_execution_artifact,
    unpack_execution_artifact,
)
from bijux_canon_index.core.errors import BijuxError
from bijux_canon_index.interfaces.cli.configuration import load_config as _load_config
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


def register_artifact_commands(artifact_app: typer.Typer) -> None:
    """Register artifact commands."""
    artifact_app.command("pack")(artifact_pack)
    artifact_app.command("unpack")(artifact_unpack)


def artifact_pack(
    ctx: typer.Context,
    run_id: str = typer.Argument(...),
    out: Path = typer.Option(Path("bundle.zip"), "--out"),  # noqa: B008
    include_vectors: bool = typer.Option(False, "--include-vectors"),
) -> None:
    """Handle artifact pack."""
    try:
        base_config = _load_config(ctx.obj.config_path) if ctx.obj else None
        config_payload = _redact_config(base_config)
        pack_execution_artifact(
            run_id=run_id,
            out=out,
            include_vectors=include_vectors,
            config_payload=config_payload,
        )
        _emit(ctx, {"status": "packed", "bundle": str(out)})
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


def artifact_unpack(
    ctx: typer.Context,
    bundle: Path = typer.Argument(...),  # noqa: B008
    out_dir: Path = typer.Option(Path("bundle_out"), "--out-dir"),  # noqa: B008
) -> None:
    """Handle artifact unpack."""
    try:
        unpack_execution_artifact(bundle=bundle, out_dir=out_dir)
        _emit(ctx, {"status": "unpacked", "path": str(out_dir)})
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


__all__ = ["register_artifact_commands"]
