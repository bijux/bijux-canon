# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""CLI entrypoint that composes command modules at the interface boundary."""

from __future__ import annotations

import os
from pathlib import Path
from typing import no_type_check

import typer

from bijux_canon_index.infra.logging import enable_trace
from bijux_canon_index.interfaces.cli.artifact_commands import (
    register_artifact_commands,
)
from bijux_canon_index.interfaces.cli.diagnostic_commands import (
    register_diagnostic_commands,
)
from bijux_canon_index.interfaces.cli.execution_commands import (
    register_execution_commands,
)
from bijux_canon_index.interfaces.cli.performance_commands import (
    register_performance_commands,
)
from bijux_canon_index.interfaces.cli.rendering import OutputOptions
from bijux_canon_index.interfaces.cli.vector_store_commands import (
    register_vector_store_commands,
)

app = typer.Typer(add_completion=False)
vdb_app = typer.Typer(add_completion=False, help="Vector DB utilities")
app.add_typer(vdb_app, name="vdb")
nd_app = typer.Typer(add_completion=False, help="ND utilities")
app.add_typer(nd_app, name="nd")
config_app = typer.Typer(add_completion=False, help="Configuration utilities")
app.add_typer(config_app, name="config")
artifact_app = typer.Typer(add_completion=False, help="Artifact bundle utilities")
app.add_typer(artifact_app, name="artifact")


@app.callback()
@no_type_check
def _main_callback(
    ctx: typer.Context,
    fmt: str | None = typer.Option(
        None,
        "--format",
        help="Output format: json|table (default: json)",
        show_default=False,
    ),
    output: Path | None = typer.Option(  # noqa: B008
        None, "--output", help="Write output to a file", show_default=False
    ),
    config: Path | None = typer.Option(  # noqa: B008
        None,
        "--config",
        help="Load configuration from a TOML/YAML file",
        show_default=False,
    ),
    trace: bool = typer.Option(False, "--trace", help="Emit trace metadata"),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress non-error output"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output"),
) -> None:
    if trace:
        enable_trace()
    if no_color:
        os.environ["RICH_NO_COLOR"] = "1"
        os.environ["TYPER_COLOR"] = "0"
    ctx.obj = OutputOptions(
        fmt=fmt,
        output=output,
        config_path=config,
        trace=trace,
        quiet=quiet,
        no_color=no_color,
    )


register_execution_commands(app)
register_vector_store_commands(vdb_app)
register_artifact_commands(artifact_app)
register_performance_commands(app, nd_app)
register_diagnostic_commands(app, config_app)


if __name__ == "__main__":
    app()
