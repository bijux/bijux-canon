# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Validation and environment diagnostics for the CLI boundary."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import typer

from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.errors import BijuxError, ValidationError
from bijux_canon_index.infra.adapters.vectorstore_registry import VECTOR_STORES
from bijux_canon_index.infra.embeddings.registry import EMBEDDING_PROVIDERS
from bijux_canon_index.infra.run_store import RunStore
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
        if config.vector_store:
            VECTOR_STORES.resolve(
                config.vector_store.backend or "memory",
                uri=config.vector_store.uri,
                options=config.vector_store.options,
            )
        if execution_contract:
            contract = _parse_contract(execution_contract)
            if config.vector_store:
                desc = VECTOR_STORES.resolve(
                    config.vector_store.backend or "memory",
                    uri=config.vector_store.uri,
                    options=config.vector_store.options,
                ).descriptor
                if (
                    contract is ExecutionContract.DETERMINISTIC
                    and not desc.deterministic_exact
                ):
                    raise ValidationError(
                        message="deterministic contract requires deterministic vector store"
                    )
                if (
                    contract is ExecutionContract.NON_DETERMINISTIC
                    and not desc.supports_ann
                ):
                    raise ValidationError(
                        message="non_deterministic contract requires ANN-capable vector store"
                    )
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
        extras = {}
        for module in ("faiss", "qdrant_client", "sentence_transformers"):
            try:
                __import__(module)
                extras[module] = True
            except Exception:
                extras[module] = False
        base_config = _load_config(ctx.obj.config_path) if ctx.obj else None
        config = _build_config(
            vector_store=vector_store,
            vector_store_uri=vector_store_uri,
            base_config=base_config,
        )
        backend_status = {"configured": False}
        if config.vector_store:
            backend_status["configured"] = True
            resolution = VECTOR_STORES.resolve(
                config.vector_store.backend or "memory",
                uri=config.vector_store.uri,
                options=config.vector_store.options,
            )
            backend_status.update(
                {
                    "backend": resolution.descriptor.name,
                    "available": resolution.descriptor.available,
                    "uri_redacted": resolution.uri_redacted,
                }
            )
            adapter = resolution.adapter
            if hasattr(adapter, "status"):
                backend_status["status"] = adapter.status()
        run_dir = RunStore()._base
        workspace = Path.cwd()
        permissions = {
            "workspace_writable": os.access(workspace, os.W_OK),
            "run_dir_writable": os.access(run_dir, os.W_OK)
            if run_dir.exists()
            else True,
        }
        report = {
            "extras": extras,
            "backend": backend_status,
            "embeddings": {"providers": EMBEDDING_PROVIDERS.providers()},
            "permissions": permissions,
        }
        _emit(ctx, report)
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


__all__ = ["doctor", "validate"]
