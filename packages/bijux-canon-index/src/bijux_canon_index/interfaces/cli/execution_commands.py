# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Command registration for the primary CLI surface."""

from __future__ import annotations

import typer

from bijux_canon_index.interfaces.cli.ingest_commands import ingest, materialize
from bijux_canon_index.interfaces.cli.query_commands import (
    compare,
    execute,
    explain,
    replay,
)
from bijux_canon_index.interfaces.cli.validation_commands import doctor, validate
from bijux_canon_index.interfaces.cli.workspace_commands import (
    audit,
    capabilities,
    init,
    list_artifacts,
    list_runs,
)


def register_execution_commands(app: typer.Typer) -> None:
    """Register execution commands."""
    app.command()(list_artifacts)
    app.command()(list_runs)
    app.command()(init)
    app.command()(capabilities)
    app.command()(audit)
    app.command()(ingest)
    app.command()(validate)
    app.command()(doctor)
    app.command()(materialize)
    app.command()(execute)
    app.command()(explain)
    app.command()(replay)
    app.command()(compare)


__all__ = ["register_execution_commands"]
