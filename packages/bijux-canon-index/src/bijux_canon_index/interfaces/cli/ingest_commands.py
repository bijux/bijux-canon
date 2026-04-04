# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Ingest and artifact materialization commands for the CLI boundary."""

from __future__ import annotations

import json
import sys

import typer

from bijux_canon_index.application.engine import VectorExecutionEngine
from bijux_canon_index.core.errors import BijuxError
from bijux_canon_index.interfaces.cli.configuration import (
    build_config as _build_config,
)
from bijux_canon_index.interfaces.cli.configuration import (
    load_config as _load_config,
)
from bijux_canon_index.interfaces.cli.configuration import (
    parse_contract as _parse_contract,
)
from bijux_canon_index.interfaces.cli.rendering import (
    config_to_dict as _config_to_dict,
)
from bijux_canon_index.interfaces.cli.rendering import emit as _emit
from bijux_canon_index.interfaces.cli.rendering import (
    resolve_correlation_id as _resolve_correlation_id,
)
from bijux_canon_index.interfaces.errors import (
    is_refusal,
    refusal_payload,
    to_cli_exit,
)
from bijux_canon_index.interfaces.errors.reporting import record_failure
from bijux_canon_index.interfaces.schemas.requests import (
    ExecutionArtifactRequest,
    IngestRequest,
)


def ingest(
    ctx: typer.Context,
    doc: str = typer.Option(..., "--doc"),
    vector: str | None = typer.Option(None, "--vector"),
    embed_model: str | None = typer.Option(None, "--embed-model"),
    embed_provider: str | None = typer.Option(None, "--embed-provider"),
    cache_embeddings: str | None = typer.Option(None, "--cache-embeddings"),
    vector_store: str | None = typer.Option(None, "--vector-store"),
    vector_store_uri: str | None = typer.Option(None, "--vector-store-uri"),
    correlation_id: str | None = typer.Option(None, "--correlation-id"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    try:
        resolved_correlation_id = _resolve_correlation_id(correlation_id)
        base_config = _load_config(ctx.obj.config_path) if ctx.obj else None
        req = IngestRequest(
            documents=[doc],
            vectors=[json.loads(vector)] if vector else None,
            embed_model=embed_model,
            embed_provider=embed_provider,
            cache_embeddings=cache_embeddings,
            correlation_id=resolved_correlation_id,
            vector_store=vector_store,
            vector_store_uri=vector_store_uri,
        )
        config = _build_config(
            vector_store=vector_store,
            vector_store_uri=vector_store_uri,
            embed_model=embed_model,
            embed_provider=embed_provider,
            cache_embeddings=cache_embeddings,
            base_config=base_config,
        )
        if dry_run:
            output = {
                "resolved_config": _config_to_dict(config),
                "determinism": "deterministic"
                if config.vector_store is None
                else "deterministic_with_vector_store",
                "provenance_fields": [
                    "vector_store_backend",
                    "vector_store_uri_redacted",
                    "vector_store_index_params",
                ]
                if config.vector_store
                else [],
            }
            _emit(ctx, output)
            return
        engine = VectorExecutionEngine(config=config)
        result = engine.ingest(req)
        _emit(ctx, result)
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


def materialize(
    ctx: typer.Context,
    execution_contract: str = typer.Option(
        ...,
        "--execution-contract",
        help="Execution contract (deterministic warns: non_deterministic loses replay guarantees)",
    ),
    index_mode: str = typer.Option(
        "exact", "--index-mode", help="Index mode: exact|ann"
    ),
    vector_store: str | None = typer.Option(None, "--vector-store"),
    vector_store_uri: str | None = typer.Option(None, "--vector-store-uri"),
) -> None:
    try:
        contract = _parse_contract(execution_contract)
        base_config = _load_config(ctx.obj.config_path) if ctx.obj else None
        engine = VectorExecutionEngine(
            config=_build_config(
                vector_store=vector_store,
                vector_store_uri=vector_store_uri,
                base_config=base_config,
            )
        )
        result = engine.materialize(
            ExecutionArtifactRequest(
                execution_contract=contract,
                index_mode=index_mode,
                vector_store=vector_store,
                vector_store_uri=vector_store_uri,
            )
        )
        _emit(ctx, result)
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


__all__ = ["ingest", "materialize"]
