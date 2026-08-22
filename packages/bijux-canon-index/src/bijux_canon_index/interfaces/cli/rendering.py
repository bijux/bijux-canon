# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Rendering and bundle helpers for the CLI boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import uuid
import zipfile

import typer

from bijux_canon_index.application.surface_services import (
    execution_trace_events,
    redact_vector_store_uri,
)
from bijux_canon_index.core.config import ExecutionConfig


@dataclass(frozen=True)
class OutputOptions:
    """Represents output options."""

    fmt: str | None = None
    output: Path | None = None
    config_path: Path | None = None
    trace: bool = False
    quiet: bool = False
    no_color: bool = False


def render_table(data: object) -> str:
    """Render table."""
    if isinstance(data, dict):
        lines = ["key | value", "---- | -----"]
        for key, value in data.items():
            lines.append(f"{key} | {value}")
        return "\n".join(lines)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        keys = list(data[0].keys())
        header = " | ".join(keys)
        divider = " | ".join(["---"] * len(keys))
        lines = [header, divider]
        lines.extend(" | ".join(str(row.get(key, "")) for key in keys) for row in data)
        return "\n".join(lines)
    return str(data)


def resolve_correlation_id(raw: str | None) -> str:
    """Resolve correlation ID."""
    return raw or f"req-{uuid.uuid4().hex}"


def emit(
    ctx: typer.Context | None,
    data: object,
    *,
    table: str | None = None,
) -> None:
    """Handle emit."""
    options: OutputOptions | None = getattr(ctx, "obj", None) if ctx else None
    fmt = options.fmt if options else None
    output = options.output if options else None
    quiet = options.quiet if options else False
    trace = options.trace if options else False

    payload: object = data
    if trace:
        payload = {"data": data, "trace": execution_trace_events()}

    if fmt == "table":
        table_payload = table or render_table(data)
        if not quiet:
            typer.echo(table_payload)
            if output:
                output.write_text(table_payload, encoding="utf-8")
        return

    if fmt is None and table is not None and not quiet:
        typer.echo(table)
    serialized = json.dumps(payload, default=str)
    if not quiet:
        typer.echo(serialized)
    if output:
        output.write_text(serialized, encoding="utf-8")


def config_to_dict(config: ExecutionConfig | None) -> dict[str, object]:
    """Handle config to dict."""
    if config is None:
        return {}
    return asdict(config)


def redact_config(config: ExecutionConfig | None) -> dict[str, object]:
    """Handle redact config."""
    payload = config_to_dict(config)
    return redact_vector_store_uri(payload)


def load_bundle(path: Path) -> dict[str, object]:
    """Load bundle."""
    with zipfile.ZipFile(path, "r") as archive:
        metadata = json.loads(archive.read("metadata.json").decode("utf-8"))
        result = json.loads(archive.read("result.json").decode("utf-8"))
        return {"metadata": metadata, "result": result}


__all__ = [
    "OutputOptions",
    "config_to_dict",
    "emit",
    "load_bundle",
    "redact_config",
    "render_table",
    "resolve_correlation_id",
]
