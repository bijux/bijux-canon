"""Command-line driver for the Bijux Agent flagship pipeline."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import sys

from bijux_agent.cli.helpers import (
    ensure_directory,
    handle_replay,
    load_config,
    process_files,
    write_final_artifacts,
)
from bijux_agent.config.env import load_environment, validate_keys
from bijux_agent.pipeline.canonical import AuditableDocPipeline
from bijux_agent.utilities.logger_manager import LoggerConfig, LoggerManager
from bijux_agent.utilities.version import get_runtime_version

DEFAULT_TASK_GOAL = "summarize this document"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
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
        default="config/config.yml",
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
        help="Path to a trace JSON file produced by bijux-agent run.",
    )
    return parser.parse_args(argv)


async def main() -> None:
    """Main entry point for Bijux Agent."""
    load_environment()
    try:
        validate_keys()
    except RuntimeError as exc:
        print(f"API key validation failed: {exc}", file=sys.stderr)
        sys.exit(1)

    args = parse_args()
    if args.command == "replay":
        handle_replay(Path(args.trace_path))
        return
    bootstrap_logger = logging.getLogger("bijux_agent.bootstrap")
    bootstrap_logger.setLevel(logging.INFO)
    if not bootstrap_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        bootstrap_logger.addHandler(handler)

    config = load_config(args.config, bootstrap_logger)
    task_goal = config.get("task_goal", DEFAULT_TASK_GOAL)

    logging_config = config.get("logging", {})
    log_dir = logging_config.get("log_dir", "artifacts/test/logs")
    log_level = logging_config.get("log_level", "INFO")
    log_file_name = logging_config.get("log_file_name", "application.log")
    structured_logging = logging_config.get("structured_logging", True)
    async_logging = logging_config.get("async_logging", True)
    telemetry_enabled = logging_config.get("telemetry_enabled", True)

    ensure_directory(log_dir)
    logger_config = LoggerConfig(
        log_dir=log_dir,
        log_level=log_level,
        log_file_name=log_file_name,
        structured_logging=structured_logging,
        async_logging=async_logging,
        telemetry_enabled=telemetry_enabled,
    )
    logger_manager = LoggerManager(name="Bijux Agent", config=logger_config)
    logger = logger_manager.get_logger()

    logger.info(
        "Bijux Agent pipeline starting",
        extra={
            "context": {
                "command": args.command,
                "input_path": args.input_path,
                "results_dir": args.results_dir,
                "task_goal": task_goal,
                "start_time": datetime.now(UTC).isoformat(),
            }
        },
    )

    replay_trace: Path | None = None
    if args.replay:
        replay_trace = Path(args.replay)
        if not replay_trace.exists():
            logger.error(f"Replay trace not found: {replay_trace}")
            sys.exit(2)
        logger.info(
            "Replay trace provided",
            extra={"context": {"replay_trace": str(replay_trace)}},
        )

    ensure_directory(args.results_dir)
    results_dir_path = Path(args.results_dir)
    pipeline = AuditableDocPipeline(
        config=config,
        logger_manager=logger_manager,
        results_dir=str(results_dir_path),
    )

    input_path = Path(args.input_path)
    if not input_path.exists():
        logger.error(f"Input path does not exist: {input_path}")
        sys.exit(2)

    if input_path.is_file():
        files = [input_path]
        logger.info("Processing single file input")
    elif input_path.is_dir():
        files = [file for file in input_path.iterdir() if file.is_file()]
        if not files:
            logger.error(
                "Input directory is empty; add documents (e.g. .txt, .md) and retry."
            )
            sys.exit(2)
        logger.info("Processing directory input")
    else:
        logger.error(
            f"Invalid input path: {input_path} (neither a file nor a directory)"
        )
        sys.exit(2)

    try:
        result = await process_files(
            pipeline,
            files,
            task_goal,
            logger,
            dry_run=args.dry_run,
        )
        logger.info(
            "Bijux Agent pipeline completed successfully",
            extra={"context": {"result": result}},
        )
        if len(files) == 1 and result["successful"]:
            print(
                json.dumps(
                    result["successful"][0]["result"], indent=2, ensure_ascii=False
                )
            )
        primary_success = result["successful"][0] if result["successful"] else None
        final_artifact = write_final_artifacts(
            success_entry=primary_success,
            results=result,
            config=config,
            task_goal=task_goal,
            results_dir=results_dir_path,
            dry_run=args.dry_run,
        )
        logger.info(
            "Final result artifact created",
            extra={"context": {"final_result": str(final_artifact)}},
        )
    except Exception:
        logger.error("Unexpected error occurred", exc_info=True)
        sys.exit(1)
    finally:
        await pipeline.shutdown()
        logger_manager.flush()
        logger.info("Bijux Agent pipeline shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Pipeline interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Pipeline failed: {e}", file=sys.stderr)
        sys.exit(1)
