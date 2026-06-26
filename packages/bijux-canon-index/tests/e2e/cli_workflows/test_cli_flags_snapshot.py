# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any, Protocol, cast

from typer.main import get_command

from bijux_canon_index.interfaces.cli import app as cli_app

SNAPSHOT_PATH = Path(__file__).with_name("cli_flags_snapshot.json")


class _CommandLike(Protocol):
    params: list[object]


class _OptionLike(Protocol):
    name: str | None
    opts: list[str]
    secondary_opts: list[str]
    required: bool
    default: Any


class _ArgumentLike(Protocol):
    name: str | None
    nargs: int
    required: bool
    default: Any


def _command_children(cmd: object) -> Mapping[str, _CommandLike] | None:
    commands = getattr(cmd, "commands", None)
    return commands if isinstance(commands, Mapping) else None


def _option_like(param: object) -> _OptionLike | None:
    if not type(param).__name__.lower().endswith("option"):
        return None
    return cast(_OptionLike, param)


def _argument_like(param: object) -> _ArgumentLike | None:
    if not type(param).__name__.lower().endswith("argument"):
        return None
    return cast(_ArgumentLike, param)


def _normalize_default(value: Any) -> Any:
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, Path):
        return str(value)
    if callable(value):
        return getattr(value, "__name__", str(value))
    return value


def _snapshot_cli() -> list[dict[str, Any]]:
    root = cast(_CommandLike, get_command(cli_app.app))
    entries: list[dict[str, Any]] = []

    def walk(cmd: _CommandLike, path: tuple[str, ...]) -> None:
        params = []
        for param in cmd.params:
            option = _option_like(param)
            if option is not None:
                params.append(
                    {
                        "param_type": "option",
                        "name": option.name,
                        "opts": sorted(option.opts + option.secondary_opts),
                        "required": option.required,
                        "default": _normalize_default(option.default),
                    }
                )
                continue
            argument = _argument_like(param)
            if argument is not None:
                params.append(
                    {
                        "param_type": "argument",
                        "name": argument.name,
                        "nargs": argument.nargs,
                        "required": argument.required,
                        "default": _normalize_default(argument.default),
                    }
                )
        entries.append(
            {
                "command": " ".join(path) if path else "root",
                "params": sorted(params, key=lambda p: (p["param_type"], p["name"])),
            }
        )
        children = _command_children(cmd)
        if children is not None:
            for name in sorted(children):
                walk(children[name], path + (name,))

    walk(root, ())
    return sorted(entries, key=lambda e: e["command"])


def test_cli_flags_snapshot_is_frozen() -> None:
    snapshot = _snapshot_cli()
    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert snapshot == expected
