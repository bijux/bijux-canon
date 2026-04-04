# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Optional Typer adapter over the package's stable stdlib CLI contract."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from bijux_canon_ingest.interfaces.cli.entrypoint import main


def _append_flag(
    argv: list[str], *, flag: str, value: str | Path | None, repeatable: bool = False
) -> None:
    if value is None:
        return
    if repeatable:
        for item in value if isinstance(value, list) else [value]:
            argv.extend((flag, str(item)))
        return
    argv.extend((flag, str(value)))


def build_app() -> Any:
    typer = importlib.import_module("typer")
    app = typer.Typer(
        add_completion=False,
        help="Optional Typer shell over the ingest package CLI entrypoint.",
    )

    @app.command()
    def pipeline(
        input_csv: Path,
        config: Path,
        set_values: list[str] | None = None,
        out: Path | None = None,
    ) -> int:
        argv = [str(input_csv), "--config", str(config)]
        _append_flag(argv, flag="--set", value=set_values, repeatable=True)
        _append_flag(argv, flag="--out", value=out)
        return main(argv)

    @app.command("index-build")
    def index_build(
        input: Path,
        out: Path,
        backend: str = "bm25",
        embedder: str = "hash16",
        sbert_model: str = "all-MiniLM-L6-v2",
        bm25_buckets: int = 2048,
        chunk_size: int = 512,
        overlap: int = 50,
    ) -> int:
        return main(
            [
                "index",
                "build",
                "--input",
                str(input),
                "--out",
                str(out),
                "--backend",
                backend,
                "--embedder",
                embedder,
                "--sbert-model",
                sbert_model,
                "--bm25-buckets",
                str(bm25_buckets),
                "--chunk-size",
                str(chunk_size),
                "--overlap",
                str(overlap),
            ]
        )

    @app.command()
    def retrieve(
        index: Path,
        query: str,
        top_k: int = 5,
        filters: list[str] | None = None,
        format: str = "json",
        out: Path | None = None,
    ) -> int:
        argv = [
            "retrieve",
            "--index",
            str(index),
            "--query",
            query,
            "--top-k",
            str(top_k),
            "--format",
            format,
        ]
        _append_flag(argv, flag="--filter", value=filters, repeatable=True)
        _append_flag(argv, flag="--out", value=out)
        return main(argv)

    @app.command()
    def ask(
        index: Path,
        query: str,
        top_k: int = 5,
        rerank: bool = True,
        filters: list[str] | None = None,
        format: str = "json",
        out: Path | None = None,
    ) -> int:
        argv = [
            "ask",
            "--index",
            str(index),
            "--query",
            query,
            "--top-k",
            str(top_k),
            "--format",
            format,
        ]
        if not rerank:
            argv.append("--no-rerank")
        _append_flag(argv, flag="--filter", value=filters, repeatable=True)
        _append_flag(argv, flag="--out", value=out)
        return main(argv)

    @app.command("eval")
    def evaluate(
        index: Path,
        suite: Path,
        backend: str = "bm25",
        top_k: int = 5,
        out: Path | None = None,
    ) -> int:
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
        _append_flag(argv, flag="--out", value=out)
        return main(argv)

    return app


__all__ = ["build_app"]
