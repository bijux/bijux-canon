# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import typer

from bijux_canon_reason.interfaces.cli import init as init_cmd
from bijux_canon_reason.interfaces.cli.main import app as main_app

app = typer.Typer(add_completion=False)
app.add_typer(main_app, name="")
app.add_typer(init_cmd.app, name="init")

__all__ = ["app"]
