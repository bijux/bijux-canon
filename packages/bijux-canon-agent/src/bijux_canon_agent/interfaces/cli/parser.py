"""Argument parser construction for the Bijux Canon Agent CLI."""

from __future__ import annotations

import argparse

from bijux_canon_agent.core.version import get_runtime_version

DEFAULT_TASK_GOAL = "summarize this document"


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Run the flagship Bijux Agent pipeline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=get_runtime_version(),
        help="Show the runtime version and exit.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser(
        "run",
        help="Process files using the auditable document pipeline.",
    )
    run_parser.add_argument(
        "input_path",
        type=str,
        help="Path to a file or directory to process.",
    )
    run_parser.add_argument(
        "--out",
        dest="results_dir",
        required=True,
        help="Directory to save structured output (JSON).",
    )
    run_parser.add_argument(
        "--config",
        type=str,
        default="examples/reference-config.yml",
        help="Path to the configuration file (YAML).",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate pipeline execution without running it.",
    )
    run_parser.add_argument(
        "--replay",
        type=str,
        default=None,
        metavar="TRACE",
        help="Optional trace file to inform replay tooling.",
    )
    replay_parser = subparsers.add_parser(
        "replay",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    replay_parser.add_argument(
        "trace_path",
        type=str,
        help="Path to a trace JSON file produced by bijux-canon-agent run.",
    )
    return parser


__all__ = ["DEFAULT_TASK_GOAL", "build_parser"]
