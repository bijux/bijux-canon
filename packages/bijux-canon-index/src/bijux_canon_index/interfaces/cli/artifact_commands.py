# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Artifact bundle commands for the CLI boundary."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import zipfile

import typer

from bijux_canon_index.application.engine import VectorExecutionEngine
from bijux_canon_index.core.errors import BijuxError
from bijux_canon_index.core.identity.ids import fingerprint
from bijux_canon_index.infra.run_store import RunStore
from bijux_canon_index.interfaces.cli.configuration import load_config as _load_config
from bijux_canon_index.interfaces.cli.rendering import (
    emit as _emit,
    redact_config as _redact_config,
)
from bijux_canon_index.interfaces.errors.reporting import record_failure
from bijux_canon_index.interfaces.errors import (
    is_refusal,
    refusal_payload,
    to_cli_exit,
)


def register_artifact_commands(artifact_app: typer.Typer) -> None:
    artifact_app.command("pack")(artifact_pack)
    artifact_app.command("unpack")(artifact_unpack)


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
        with zipfile.ZipFile(out, "w") as archive:
            archive.writestr("metadata.json", json.dumps(bundle["metadata"], indent=2))
            archive.writestr("result.json", json.dumps(bundle["result"], indent=2))
            archive.writestr("config.json", json.dumps(bundle["config"], indent=2))
            archive.writestr(
                "vector_hashes.json", json.dumps(bundle["vector_hashes"], indent=2)
            )
            if include_vectors:
                archive.writestr("vectors.json", json.dumps(vectors_payload, indent=2))
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
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(bundle, "r") as archive:
            archive.extractall(out_dir)
        _emit(ctx, {"status": "unpacked", "path": str(out_dir)})
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


__all__ = ["register_artifact_commands"]
