# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Argument-vector builders for the optional Typer shell."""

from __future__ import annotations

from pathlib import Path


def append_flag(
    argv: list[str],
    *,
    flag: str,
    value: str | Path | list[str] | None,
    repeatable: bool = False,
) -> None:
    """Append a CLI flag and optional value to an argv list."""

    if value is None:
        return
    if repeatable:
        if isinstance(value, list):
            for item in value:
                argv.extend((flag, str(item)))
            return
        argv.extend((flag, str(value)))
        return
    argv.extend((flag, str(value)))


def build_pipeline_argv(
    *,
    input_csv: Path,
    config: Path,
    set_values: list[str] | None = None,
    out: Path | None = None,
) -> list[str]:
    argv = [str(input_csv), "--config", str(config)]
    append_flag(argv, flag="--set", value=set_values, repeatable=True)
    append_flag(argv, flag="--out", value=out)
    return argv


def build_retrieve_argv(
    *,
    index: Path,
    query: str,
    top_k: int,
    filters: list[str] | None,
    output_format: str,
    out: Path | None,
) -> list[str]:
    argv = [
        "retrieve",
        "--index",
        str(index),
        "--query",
        query,
        "--top-k",
        str(top_k),
        "--format",
        output_format,
    ]
    append_flag(argv, flag="--filter", value=filters, repeatable=True)
    append_flag(argv, flag="--out", value=out)
    return argv


def build_ask_argv(
    *,
    index: Path,
    query: str,
    top_k: int,
    rerank: bool,
    filters: list[str] | None,
    output_format: str,
    out: Path | None,
) -> list[str]:
    argv = [
        "ask",
        "--index",
        str(index),
        "--query",
        query,
        "--top-k",
        str(top_k),
        "--format",
        output_format,
    ]
    if not rerank:
        argv.append("--no-rerank")
    append_flag(argv, flag="--filter", value=filters, repeatable=True)
    append_flag(argv, flag="--out", value=out)
    return argv


def build_eval_argv(
    *,
    index: Path,
    suite: Path,
    backend: str,
    top_k: int,
    out: Path | None,
) -> list[str]:
    argv = [
        "eval",
        "--index",
        str(index),
        "--suite",
        str(suite),
        "--backend",
        backend,
        "--top-k",
        str(top_k),
    ]
    append_flag(argv, flag="--out", value=out)
    return argv


__all__ = [
    "append_flag",
    "build_ask_argv",
    "build_eval_argv",
    "build_pipeline_argv",
    "build_retrieve_argv",
]
