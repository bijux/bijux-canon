# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG Core 6: optional Typer CLI (end-of-Bijux RAG).

# pyright: reportUnusedFunction=false

This is an optional shell. It is behind a dynamic import guard so the repo does
not require `typer` to be installed to import/run tests.
"""

# mypy: ignore-errors

from __future__ import annotations

import importlib
from typing import Any


def build_app() -> Any:
    typer = importlib.import_module("typer")
    app = typer.Typer()

    @app.command()
    def hello(name: str = "world") -> None:
        typer.echo(f"hello {name}")

    return app


__all__ = ["build_app"]
