# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Parser construction for the explicit Runtime v2 command group."""

from __future__ import annotations

import argparse


def add_v2_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Add stable v2 commands without changing frozen v1 command meanings."""
    v2 = subparsers.add_parser(
        "v2",
        help="Typed local-first corpus, index, reasoning, and Runtime operations.",
    )
    commands = v2.add_subparsers(dest="v2_command", required=True)

    discover = commands.add_parser("discover", help="Discover immutable local sources.")
    discover.add_argument("directory")
    discover.add_argument("--root-name", default="corpus")
    discover.add_argument("--include", action="append", default=[])
    discover.add_argument("--exclude", action="append", default=[])
    discover.add_argument(
        "--symlink-policy",
        choices=("reject", "files_within_root", "all_within_root"),
        default="reject",
    )

    for name in ("ingest", "index", "retrieve", "ask", "research", "run"):
        command = commands.add_parser(name, help=f"Submit the typed {name} operation.")
        command.add_argument("--request", required=True)
        command.add_argument("--idempotency-key", required=True)

    corpus_inspect = commands.add_parser(
        "corpus-inspect", help="Inspect an immutable corpus snapshot."
    )
    corpus_inspect.add_argument("corpus_id")

    index_inspect = commands.add_parser(
        "index-inspect", help="Inspect an immutable index generation."
    )
    index_inspect.add_argument("index_id")
    index_inspect.add_argument("--cursor")
    index_inspect.add_argument("--offset", type=int)
    index_inspect.add_argument("--limit", type=int, default=100)

    status = commands.add_parser("status", help="Inspect durable job state.")
    status.add_argument("job_id")

    result = commands.add_parser("result", help="Resolve a completed job result.")
    result.add_argument("job_id")

    inspect = commands.add_parser("inspect", help="Inspect a persisted Runtime run.")
    inspect.add_argument("run_id")
    inspect.add_argument("--attempt-id")
    inspect.add_argument("--cursor")
    inspect.add_argument("--offset", type=int)
    inspect.add_argument("--limit", type=int, default=100)

    replay = commands.add_parser("replay", help="Submit a linked replay attempt.")
    replay.add_argument("run_id")
    replay.add_argument("--request", required=True)
    replay.add_argument("--idempotency-key", required=True)

    compare = commands.add_parser("compare", help="Compare immutable attempts.")
    compare.add_argument("--request", required=True)

    cancel = commands.add_parser("cancel", help="Cancel queued or running work.")
    cancel.add_argument("job_id")
    cancel.add_argument("--request", required=True)
    cancel.add_argument("--idempotency-key", required=True)


__all__ = ["add_v2_commands"]
