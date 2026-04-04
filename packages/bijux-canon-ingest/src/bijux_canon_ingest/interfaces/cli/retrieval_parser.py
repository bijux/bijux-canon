# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Argument parser construction for retrieval-oriented CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_retrieval_parser() -> argparse.ArgumentParser:
    """Build the retrieval-mode parser with all supported subcommands."""

    parser = argparse.ArgumentParser(prog="bijux-canon-ingest")
    subcommands = parser.add_subparsers(dest="cmd", required=True)

    index_parser = subcommands.add_parser("index", help="Index operations")
    index_subcommands = index_parser.add_subparsers(dest="index_cmd", required=True)
    build_parser = index_subcommands.add_parser("build", help="Build an index from CSV")
    build_parser.add_argument("--input", type=Path, required=True)
    build_parser.add_argument("--out", type=Path, required=True)
    build_parser.add_argument(
        "--backend", choices=["bm25", "numpy-cosine"], default="bm25"
    )
    build_parser.add_argument(
        "--embedder", choices=["hash16", "sbert"], default="hash16"
    )
    build_parser.add_argument("--sbert-model", default="all-MiniLM-L6-v2")
    build_parser.add_argument("--bm25-buckets", type=int, default=2048)
    build_parser.add_argument("--chunk-size", type=int, default=128)
    build_parser.add_argument("--overlap", type=int, default=0)
    build_parser.add_argument("--tail-policy", default="emit_short")

    retrieve_parser = subcommands.add_parser("retrieve", help="Retrieve top-k chunks")
    retrieve_parser.add_argument("--index", type=Path, required=True)
    retrieve_parser.add_argument("--query", required=True)
    retrieve_parser.add_argument("--top-k", type=int, default=5)
    retrieve_parser.add_argument(
        "--filter",
        action="append",
        default=[],
        help="Filter k=v (repeatable)",
    )
    retrieve_parser.add_argument("--out", type=Path, default=None)

    ask_parser = subcommands.add_parser(
        "ask", help="Answer with citations (extractive)"
    )
    ask_parser.add_argument("--index", type=Path, required=True)
    ask_parser.add_argument("--query", required=True)
    ask_parser.add_argument("--top-k", type=int, default=5)
    ask_parser.add_argument(
        "--filter",
        action="append",
        default=[],
        help="Filter k=v (repeatable)",
    )
    ask_parser.add_argument("--no-rerank", action="store_true")
    ask_parser.add_argument("--format", choices=["json", "yaml"], default="json")
    ask_parser.add_argument("--out", type=Path, default=None)

    eval_parser = subcommands.add_parser(
        "eval", help="Evaluate retrieval vs a query suite"
    )
    eval_parser.add_argument("--index", type=Path, required=True)
    eval_parser.add_argument(
        "--suite",
        type=Path,
        required=True,
        help="Directory containing queries.jsonl",
    )
    eval_parser.add_argument("--k", type=int, default=10)
    eval_parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Optional baseline metrics JSON",
    )
    eval_parser.add_argument("--tolerance", type=float, default=0.0)
    return parser


__all__ = ["build_retrieval_parser"]
