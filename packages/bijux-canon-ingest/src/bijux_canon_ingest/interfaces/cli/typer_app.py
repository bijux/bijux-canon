# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Optional Typer adapter over the package's stable stdlib CLI contract."""

from __future__ import annotations

import importlib
from pathlib import Path
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, cast

from bijux_canon_ingest.interfaces.cli.entrypoint import main
from bijux_canon_ingest.interfaces.cli.typer_argv import (
    build_ask_argv,
    build_eval_argv,
    build_pipeline_argv,
    build_retrieve_argv,
)

if TYPE_CHECKING:
    _Fn = TypeVar("_Fn", bound=Callable[..., object])

    class _TyperApp(Protocol):
        def command(
            self, name: str | None = None, /, *args: Any, **kwargs: Any
        ) -> Callable[[_Fn], _Fn]: ...


def build_app() -> Any:
    typer = importlib.import_module("typer")
    app = typer.Typer(
        add_completion=False,
        help="Optional Typer shell over the ingest package CLI entrypoint.",
    )
    typed_app = cast("_TyperApp", app)

    @typed_app.command()
    def pipeline(
        input_csv: Path,
        config: Path,
        set_values: list[str] | None = None,
        out: Path | None = None,
    ) -> int:
        return main(
            build_pipeline_argv(
                input_csv=input_csv,
                config=config,
                set_values=set_values,
                out=out,
            )
        )

    @typed_app.command("index-build")
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

    @typed_app.command()
    def retrieve(
        index: Path,
        query: str,
        top_k: int = 5,
        filters: list[str] | None = None,
        format: str = "json",
        out: Path | None = None,
    ) -> int:
        return main(
            build_retrieve_argv(
                index=index,
                query=query,
                top_k=top_k,
                filters=filters,
                output_format=format,
                out=out,
            )
        )

    @typed_app.command()
    def ask(
        index: Path,
        query: str,
        top_k: int = 5,
        rerank: bool = True,
        filters: list[str] | None = None,
        format: str = "json",
        out: Path | None = None,
    ) -> int:
        return main(
            build_ask_argv(
                index=index,
                query=query,
                top_k=top_k,
                rerank=rerank,
                filters=filters,
                output_format=format,
                out=out,
            )
        )

    @typed_app.command("eval")
    def evaluate(
        index: Path,
        suite: Path,
        backend: str = "bm25",
        top_k: int = 5,
        out: Path | None = None,
    ) -> int:
        return main(
            build_eval_argv(
                index=index,
                suite=suite,
                backend=backend,
                top_k=top_k,
                out=out,
            )
        )

    return app


__all__ = ["build_app"]
