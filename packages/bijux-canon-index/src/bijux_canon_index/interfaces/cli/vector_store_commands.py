# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Vector store maintenance commands for the CLI boundary."""

from __future__ import annotations

from dataclasses import replace
import json
import sys

import typer

from bijux_canon_index.application.engine import VectorExecutionEngine
from bijux_canon_index.core.errors import BijuxError, ValidationError
from bijux_canon_index.interfaces.cli.configuration import build_config as _build_config
from bijux_canon_index.interfaces.cli.rendering import emit as _emit
from bijux_canon_index.interfaces.errors import (
    is_refusal,
    refusal_payload,
)
from bijux_canon_index.interfaces.errors.reporting import record_failure


def register_vector_store_commands(vdb_app: typer.Typer) -> None:
    vdb_app.command("status")(vdb_status)
    vdb_app.command("rebuild")(vdb_rebuild)
    vdb_app.command("compact")(vdb_compact)


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


__all__ = ["register_vector_store_commands"]
