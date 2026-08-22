# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Thin CLI transport for immutable index-generation operations."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import typer

from bijux_canon_index.application.surface_services import (
    index_service_from_environment,
)
from bijux_canon_index.interfaces.cli.rendering import emit
from bijux_canon_index.interfaces.schemas.index_generations import (
    IndexBuildRequestPayload,
    IndexInspectionResponse,
    IndexQueryRequestPayload,
    IndexQueryResponse,
)

REQUEST_PATH_OPTION = typer.Option(..., "--request", exists=True, dir_okay=False)
REGISTRY_ROOT_OPTION = typer.Option(None, "--registry-root", file_okay=False)
GENERATION_ID_OPTION = typer.Option(..., "--generation-id")
OPTIONAL_GENERATION_ID_OPTION = typer.Option(None, "--generation-id")


def register_index_generation_commands(index_app: typer.Typer) -> None:
    """Register persistent generation commands on one transport group."""

    index_app.command("build")(build_generation)
    index_app.command("activate")(activate_generation)
    index_app.command("inspect")(inspect_generation)
    index_app.command("verify")(verify_generation)
    index_app.command("query")(query_generation)


def _load_payload(
    path: Path, model: type[IndexBuildRequestPayload]
) -> IndexBuildRequestPayload:
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def _fail(error: Exception) -> NoReturn:
    typer.echo(str(error), err=True)
    raise typer.Exit(code=1) from error


def build_generation(
    ctx: typer.Context,
    request: Path = REQUEST_PATH_OPTION,
    registry_root: Path | None = REGISTRY_ROOT_OPTION,
) -> None:
    """Build and admit one coherent immutable generation from a JSON request."""

    try:
        payload = _load_payload(request, IndexBuildRequestPayload)
        report = index_service_from_environment(registry_root=registry_root).build(
            (chunk.to_domain() for chunk in payload.chunks),
            snapshot_artifact_id=payload.snapshot_artifact_id,
            model_lock_artifact_id=payload.model_lock_artifact_id,
            limits=payload.limits.to_domain(),
            hnsw_parameters=payload.hnsw_parameters.to_domain(),
            activate=payload.activate,
        )
        emit(ctx, IndexInspectionResponse.from_report(report).model_dump(mode="json"))
    except Exception as error:
        _fail(error)


def activate_generation(
    ctx: typer.Context,
    generation_id: str = GENERATION_ID_OPTION,
    registry_root: Path | None = REGISTRY_ROOT_OPTION,
) -> None:
    """Atomically activate one admitted immutable generation."""

    try:
        report = index_service_from_environment(registry_root=registry_root).activate(
            generation_id
        )
        emit(ctx, IndexInspectionResponse.from_report(report).model_dump(mode="json"))
    except Exception as error:
        _fail(error)


def inspect_generation(
    ctx: typer.Context,
    generation_id: str | None = OPTIONAL_GENERATION_ID_OPTION,
    registry_root: Path | None = REGISTRY_ROOT_OPTION,
) -> None:
    """Inspect one admitted generation without exposing content or secrets."""

    try:
        report = index_service_from_environment(registry_root=registry_root).inspect(
            generation_id
        )
        emit(ctx, IndexInspectionResponse.from_report(report).model_dump(mode="json"))
    except Exception as error:
        _fail(error)


def verify_generation(
    ctx: typer.Context,
    generation_id: str | None = OPTIONAL_GENERATION_ID_OPTION,
    registry_root: Path | None = REGISTRY_ROOT_OPTION,
) -> None:
    """Verify integrity and model compatibility for one admitted generation."""

    try:
        report = index_service_from_environment(registry_root=registry_root).verify(
            generation_id
        )
        emit(ctx, IndexInspectionResponse.from_report(report).model_dump(mode="json"))
    except Exception as error:
        _fail(error)


def query_generation(
    ctx: typer.Context,
    request: Path = REQUEST_PATH_OPTION,
    registry_root: Path | None = REGISTRY_ROOT_OPTION,
) -> None:
    """Query one verified immutable generation from a JSON request."""

    try:
        payload = IndexQueryRequestPayload.model_validate_json(
            request.read_text(encoding="utf-8")
        )
        report = index_service_from_environment(registry_root=registry_root).query(
            payload.to_domain(),
            generation_id=payload.generation_id,
        )
        emit(ctx, IndexQueryResponse.from_report(report).model_dump(mode="json"))
    except Exception as error:
        _fail(error)


__all__ = ["register_index_generation_commands"]
