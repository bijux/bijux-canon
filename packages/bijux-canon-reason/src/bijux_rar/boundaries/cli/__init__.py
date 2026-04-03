# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import typer

from bijux_rar.boundaries.cli import init as init_cmd
from bijux_rar.boundaries.cli.main import app as main_app

app = typer.Typer(add_completion=False)
app.add_typer(main_app, name="")
app.add_typer(init_cmd.app, name="init")

__all__ = ["app"]
