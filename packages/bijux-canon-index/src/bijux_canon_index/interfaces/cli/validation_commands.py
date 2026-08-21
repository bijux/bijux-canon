# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Validation and environment diagnostics for the CLI boundary."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import typer

from bijux_canon_index.core.errors import BijuxError, ValidationError
from bijux_canon_index.application.surface_services import (
    environment_report,
    validate_vector_store,
)
from bijux_canon_index.interfaces.cli.configuration import (
    build_config as _build_config,
)
from bijux_canon_index.interfaces.cli.configuration import (
    load_config as _load_config,
)
from bijux_canon_index.interfaces.cli.configuration import (
    parse_contract as _parse_contract,
)
from bijux_canon_index.interfaces.cli.rendering import emit as _emit
from bijux_canon_index.interfaces.errors import (
    is_refusal,
    refusal_payload,
    to_cli_exit,
)
from bijux_canon_index.interfaces.errors.reporting import record_failure


def validate(
    ctx: typer.Context,
    doc: list[str] = typer.Option(None, "--doc"),  # noqa: B008
    vector: list[str] = typer.Option(None, "--vector"),  # noqa: B008
    execution_contract: str | None = typer.Option(None, "--execution-contract"),
    vector_store: str | None = typer.Option(None, "--vector-store"),
    vector_store_uri: str | None = typer.Option(None, "--vector-store-uri"),
) -> None:
    """Validate ctx."""
    try:
        docs = doc or []
        vectors = [json.loads(v) for v in (vector or [])]
        if docs and vectors and len(docs) != len(vectors):
            raise ValidationError(message="doc/vector alignment mismatch")
        if vectors:
            dims = {len(v) for v in vectors}
            if len(dims) != 1:
                raise ValidationError(message="vectors have inconsistent dimensions")
        base_config = _load_config(ctx.obj.config_path) if ctx.obj else None
        config = _build_config(
            vector_store=vector_store,
            vector_store_uri=vector_store_uri,
            base_config=base_config,
        )
        contract = _parse_contract(execution_contract) if execution_contract else None
        validate_vector_store(config=config, contract=contract)
        _emit(ctx, {"status": "valid"})
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


def doctor(
    ctx: typer.Context,
    vector_store: str | None = typer.Option(None, "--vector-store"),
    vector_store_uri: str | None = typer.Option(None, "--vector-store-uri"),
) -> None:
    """Handle doctor."""
    try:
        base_config = _load_config(ctx.obj.config_path) if ctx.obj else None
        config = _build_config(
            vector_store=vector_store,
            vector_store_uri=vector_store_uri,
            base_config=base_config,
        )
        _emit(ctx, environment_report(config=config, workspace=Path.cwd()))
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


__all__ = ["doctor", "validate"]
