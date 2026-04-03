# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

import typer

from bijux_rar.boundaries.serde.json_file import write_json_file

app = typer.Typer(add_completion=False, help="Project scaffolding helpers.")


_DEFAULT_TARGET = Path("specs")
TARGET_OPTION = typer.Option(
    None, "--target", help="Where to place samples (default: specs)"
)


@app.command("init")
def init_project(target: Path = TARGET_OPTION) -> None:
    target = target or _DEFAULT_TARGET
    target.mkdir(parents=True, exist_ok=True)
    sample_spec = target / "sample_spec.json"
    if not sample_spec.exists():
        write_json_file(
            sample_spec,
            {
                "description": "Return the capital of France.",
                "constraints": {"domain": "geography"},
                "expected_output_type": "Claim",
                "version": 1,
            },
        )
    typer.echo(f"Initialized sample spec at {sample_spec}")
