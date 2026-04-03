# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Stdlib CLI entrypoint for ingest pipeline and retrieval commands."""

from __future__ import annotations

import sys

from bijux_canon_ingest.interfaces.cli.pipeline_commands import run_pipeline_commands
from bijux_canon_ingest.interfaces.cli.retrieval_commands import run_retrieval_commands

_RETRIEVAL_COMMANDS = {"index", "retrieve", "ask", "eval"}


def main(argv: list[str] | None = None) -> int:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    if argv_list and argv_list[0] in _RETRIEVAL_COMMANDS:
        return run_retrieval_commands(argv_list)
    return run_pipeline_commands(argv_list)


__all__ = ["main"]
