# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Parser construction for the explicit Runtime v2 command group."""

from __future__ import annotations

import argparse

_PROFILES = (
    "offline-lexical",
    "local-hybrid-exact",
    "local-hybrid-ann",
    "qdrant-hybrid",
)


def _add_operation_options(command: argparse.ArgumentParser) -> None:
    command.add_argument(
        "--request",
        help="Optional strict v2 request JSON; direct path/options remain supported.",
    )
    command.add_argument(
        "--idempotency-key",
        help="Stable retry identity; defaults to the generated or supplied request ID.",
    )
    command.add_argument("--request-id", help="Stable caller request identity.")
    command.add_argument("--scope", default="local")
    command.add_argument("--profile", choices=_PROFILES, default="offline-lexical")
    command.add_argument("--operation-timeout-seconds", type=float, default=30.0)
    command.add_argument("--max-artifact-bytes", type=int, default=10_000_000)
    command.add_argument("--max-steps", type=int)
    command.add_argument("--max-provider-tokens", type=int)
    command.add_argument(
        "--wait",
        action="store_true",
        help="Wait for a terminal job state instead of returning after submission.",
    )
    command.add_argument(
        "--wait-timeout-seconds",
        type=float,
        default=30.0,
        help="Maximum operator wait; job execution retains its own request budget.",
    )


def _add_retrieval_options(command: argparse.ArgumentParser) -> None:
    command.add_argument("query", nargs="?")
    command.add_argument("--index-id")
    command.add_argument("--top-k", type=int, default=5)
    command.add_argument("--document-id", action="append", default=[])
    command.add_argument("--source-uri", action="append", default=[])


def _add_answer_options(command: argparse.ArgumentParser) -> None:
    _add_retrieval_options(command)
    command.add_argument("--corpus-id")
    command.add_argument("--provider", default="credential-free")


def add_v2_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Add stable v2 commands without changing frozen v1 command meanings."""
    v2 = subparsers.add_parser(
        "v2",
        help="Typed local-first corpus, index, reasoning, and Runtime operations.",
    )
    v2.add_argument(
        "--correlation-id",
        help="Stable caller correlation identity included in typed failures.",
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

    commands.add_parser("live", help="Report dependency-free process liveness.")
    capabilities = commands.add_parser(
        "capabilities",
        help="Inspect effective configuration and installed product capabilities.",
    )
    capabilities.add_argument(
        "--human",
        action="store_true",
        help="Render the same discovery report as operator-oriented text.",
    )
    ready = commands.add_parser("ready", help="Verify capability-aware readiness.")
    ready.add_argument(
        "--operation",
        choices=(
            "initialized",
            "ingest",
            "index",
            "retrieve",
            "ask",
            "research",
            "run",
        ),
        default="initialized",
    )
    ready.add_argument(
        "--profile",
        choices=_PROFILES,
        help="Evaluate dependencies for one exact execution profile.",
    )

    ingest = commands.add_parser(
        "ingest", help="Prepare a durable corpus from a document directory."
    )
    ingest.add_argument("source_directory", nargs="?")
    _add_operation_options(ingest)

    index = commands.add_parser("index", help="Build indexes for a corpus identity.")
    index.add_argument("corpus_id", nargs="?")
    _add_operation_options(index)

    for name in ("search", "retrieve"):
        search = commands.add_parser(
            name,
            help=(
                "Search an immutable index for bounded evidence."
                if name == "search"
                else "Retrieve bounded evidence (automation-compatible search alias)."
            ),
        )
        _add_retrieval_options(search)
        _add_operation_options(search)

    for name in ("ask", "research"):
        answer = commands.add_parser(name, help=f"Submit a grounded {name} operation.")
        _add_answer_options(answer)
        _add_operation_options(answer)

    run = commands.add_parser("run", help="Run the complete linked workflow.")
    run.add_argument("query", nargs="?")
    run.add_argument("--source-directory")
    run.add_argument("--corpus-id")
    run.add_argument("--top-k", type=int, default=5)
    run.add_argument("--document-id", action="append", default=[])
    run.add_argument("--source-uri", action="append", default=[])
    run.add_argument("--provider", default="credential-free")
    _add_operation_options(run)

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

    for name, help_text in (
        (
            "evaluate-retrieval",
            "Execute reviewed questions through the installed persistent retriever.",
        ),
        (
            "search-retrieval-configurations",
            "Search general hybrid configurations using development truth only.",
        ),
    ):
        retrieval_evaluation = commands.add_parser(name, help=help_text)
        retrieval_evaluation.add_argument("--cases", required=True)
        retrieval_evaluation.add_argument("--qrels", required=True)
        retrieval_evaluation.add_argument("--index-id", required=True)
        retrieval_evaluation.add_argument("--split", default="development")
        retrieval_evaluation.add_argument(
            "--mode",
            choices=("offline-lexical", "local-hybrid-exact", "local-hybrid-ann"),
            default="local-hybrid-ann",
        )
        retrieval_evaluation.add_argument("--top-k", type=int, default=10)
        retrieval_evaluation.add_argument("--human", action="store_true")

    answer_evaluation = commands.add_parser(
        "evaluate-answer",
        help="Adapt one persisted grounded answer into output-only evaluation input.",
    )
    answer_evaluation.add_argument("run_id")
    answer_evaluation.add_argument("--attempt-id")
    answer_evaluation.add_argument("--case-id", required=True)
    answer_evaluation.add_argument("--question", required=True)

    status = commands.add_parser("status", help="Inspect durable job state.")
    status.add_argument("job_id")
    status.add_argument(
        "--follow",
        action="store_true",
        help="Wait for terminal state using worker notifications.",
    )
    status.add_argument("--timeout-seconds", type=float, default=30.0)

    result = commands.add_parser("result", help="Resolve a completed job result.")
    result.add_argument("job_id")

    inspect = commands.add_parser("inspect", help="Inspect a persisted Runtime run.")
    inspect.add_argument("run_id")
    inspect.add_argument("--attempt-id")
    inspect.add_argument("--cursor")
    inspect.add_argument("--offset", type=int)
    inspect.add_argument("--limit", type=int, default=5)

    artifact_payload = commands.add_parser(
        "artifact-payload",
        help="Read one bounded page of immutable artifact payload bytes.",
    )
    artifact_payload.add_argument("artifact_id")
    artifact_payload.add_argument("--offset", type=int, default=0)
    artifact_payload.add_argument("--max-bytes", type=int, default=64 * 1024)

    replay = commands.add_parser("replay", help="Submit a linked replay attempt.")
    replay.add_argument("run_id")
    replay.add_argument("--request")
    replay.add_argument("--request-id")
    replay.add_argument("--source-attempt-id")
    replay.add_argument("--process-id", default="operator-cli")
    replay.add_argument(
        "--network-policy",
        choices=("disabled", "recorded-only", "permitted"),
        default="disabled",
    )
    replay.add_argument("--provider-allowlist", action="append", default=[])
    replay.add_argument("--job-timeout-seconds", type=float)
    replay.add_argument("--idempotency-key")
    replay.add_argument("--wait", action="store_true")
    replay.add_argument("--wait-timeout-seconds", type=float, default=30.0)

    compare = commands.add_parser("compare", help="Compare immutable attempts.")
    compare.add_argument("baseline_run_id", nargs="?")
    compare.add_argument("candidate_run_id", nargs="?")
    compare.add_argument("--baseline-attempt-id")
    compare.add_argument("--candidate-attempt-id")
    compare.add_argument("--dimension", action="append", default=[])
    compare.add_argument("--limit", type=int, default=100)
    compare.add_argument("--cursor")
    compare.add_argument("--request")
    compare.add_argument("--request-id")

    cancel = commands.add_parser("cancel", help="Cancel queued or running work.")
    cancel.add_argument("job_id")
    cancel.add_argument("--request")
    cancel.add_argument("--request-id")
    cancel.add_argument("--reason", default="operator requested cancellation")
    cancel.add_argument("--idempotency-key")

    backup = commands.add_parser(
        "backup", help="Create a verified backup of the configured Runtime store."
    )
    backup.add_argument("backup_id")
    backup.add_argument("--created-at")

    restore = commands.add_parser(
        "restore", help="Restore a verified backup into a new local root."
    )
    restore.add_argument("backup_generation")
    restore.add_argument("restore_root")


__all__ = ["add_v2_commands"]
