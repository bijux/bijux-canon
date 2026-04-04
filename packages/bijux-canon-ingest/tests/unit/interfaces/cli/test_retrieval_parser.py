# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

from bijux_canon_ingest.interfaces.cli.retrieval_parser import build_retrieval_parser


def test_retrieval_parser_parses_index_build_command() -> None:
    parser = build_retrieval_parser()

    args = parser.parse_args(
        ["index", "build", "--input", "docs.csv", "--out", "index.msgpack"]
    )

    assert args.cmd == "index"
    assert args.index_cmd == "build"
    assert args.input == Path("docs.csv")
    assert args.out == Path("index.msgpack")


def test_retrieval_parser_parses_ask_command() -> None:
    parser = build_retrieval_parser()

    args = parser.parse_args(
        ["ask", "--index", "index.msgpack", "--query", "powerhouse", "--no-rerank"]
    )

    assert args.cmd == "ask"
    assert args.index == Path("index.msgpack")
    assert args.query == "powerhouse"
    assert args.no_rerank is True
