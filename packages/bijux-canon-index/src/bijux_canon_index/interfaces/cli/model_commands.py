# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Installed CLI transport for the validated local model lifecycle."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import typer

from bijux_canon_index.application.model_lifecycle import (
    ModelLifecycleError,
    acquire_model,
    register_existing_model,
    validate_model,
)
from bijux_canon_index.infra.embeddings.model_cache import ModelMaterializationError
from bijux_canon_index.interfaces.cli.rendering import emit

PROFILE_OPTION = typer.Option(
    "local-minilm-384",
    "--profile",
    help="Pinned model profile identifier.",
)
CACHE_ROOT_OPTION = typer.Option(
    ...,
    "--cache-root",
    file_okay=False,
    help="Revision-addressed destination cache.",
)
MODEL_ROOT_OPTION = typer.Option(
    ...,
    "--model-root",
    file_okay=False,
    help="Directory containing the pinned model files.",
)


def register_model_commands(model_app: typer.Typer) -> None:
    """Register acquisition, registration, and offline validation commands."""

    model_app.command("acquire")(acquire)
    model_app.command("register")(register)
    model_app.command("validate")(validate)


def _fail(error: Exception) -> NoReturn:
    typer.echo(str(error), err=True)
    raise typer.Exit(code=1) from error


def acquire(
    ctx: typer.Context,
    cache_root: Path = CACHE_ROOT_OPTION,
    profile: str = PROFILE_OPTION,
) -> None:
    """Acquire a pinned model and prove bounded CPU inference for offline reuse."""

    try:
        emit(ctx, acquire_model(cache_root, profile_id=profile).record())
    except (ModelLifecycleError, ModelMaterializationError) as error:
        _fail(error)


def register(
    ctx: typer.Context,
    model_root: Path = MODEL_ROOT_OPTION,
    profile: str = PROFILE_OPTION,
) -> None:
    """Bind existing pinned files to a lock and prove offline CPU inference."""

    try:
        emit(ctx, register_existing_model(model_root, profile_id=profile).record())
    except (ModelLifecycleError, ModelMaterializationError) as error:
        _fail(error)


def validate(
    ctx: typer.Context,
    model_root: Path = MODEL_ROOT_OPTION,
    profile: str = PROFILE_OPTION,
) -> None:
    """Recheck exact files, compatibility, dimension, and offline CPU inference."""

    try:
        emit(ctx, validate_model(model_root, profile_id=profile).record())
    except (ModelLifecycleError, ModelMaterializationError) as error:
        _fail(error)


__all__ = ["register_model_commands"]
