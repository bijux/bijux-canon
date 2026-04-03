# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click
from typer.main import get_command

from bijux_vex.boundaries.cli import app as cli_app


SNAPSHOT_PATH = Path(__file__).with_name("cli_flags_snapshot.json")


def _normalize_default(value: Any) -> Any:
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, Path):
        return str(value)
    if callable(value):
        return getattr(value, "__name__", str(value))
    return value


def _snapshot_cli() -> list[dict[str, Any]]:
    root = get_command(cli_app.app)
    entries: list[dict[str, Any]] = []

    def walk(cmd: click.Command, path: tuple[str, ...]) -> None:
        params = []
        for param in cmd.params:
            if isinstance(param, click.Option):
                params.append(
                    {
                        "param_type": "option",
                        "name": param.name,
                        "opts": sorted(param.opts + param.secondary_opts),
                        "required": param.required,
                        "default": _normalize_default(param.default),
                    }
                )
            elif isinstance(param, click.Argument):
                params.append(
                    {
                        "param_type": "argument",
                        "name": param.name,
                        "nargs": param.nargs,
                        "required": param.required,
                        "default": _normalize_default(param.default),
                    }
                )
        entries.append(
            {
                "command": " ".join(path) if path else "root",
                "params": sorted(params, key=lambda p: (p["param_type"], p["name"])),
            }
        )
        if isinstance(cmd, click.Group):
            for name in sorted(cmd.commands):
                walk(cmd.commands[name], path + (name,))

    walk(root, ())
    return sorted(entries, key=lambda e: e["command"])


def test_cli_flags_snapshot_is_frozen() -> None:
    snapshot = _snapshot_cli()
    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert snapshot == expected
