"""Command-line driver for the Bijux Canon Agent pipeline."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import json
from pathlib import Path
import sys

from bijux_canon_agent.interfaces.cli.helpers import (
    handle_replay,
    load_config,
    process_files,
    write_final_artifacts,
)
from bijux_canon_agent.interfaces.cli.parser import DEFAULT_TASK_GOAL, build_parser
from bijux_canon_agent.interfaces.cli.runtime_setup import (
    create_bootstrap_logger,
    create_logger_manager,
    resolve_input_files,
)
from bijux_canon_agent.config.env import load_environment, validate_keys
from bijux_canon_agent.pipeline.canonical import AuditableDocPipeline


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = build_parser()
    return parser.parse_args(argv)


async def main() -> None:
    """Main entry point for Bijux Canon Agent."""
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
    bootstrap_logger = create_bootstrap_logger()
    config = load_config(args.config, bootstrap_logger)
    task_goal = config.get("task_goal", DEFAULT_TASK_GOAL)
    logger_manager = create_logger_manager(config)
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

    results_dir_path = Path(args.results_dir)
    results_dir_path.mkdir(parents=True, exist_ok=True)
    pipeline = AuditableDocPipeline(
        config=config,
        logger_manager=logger_manager,
        results_dir=str(results_dir_path),
    )

    input_path = Path(args.input_path)
    try:
        files = resolve_input_files(input_path)
    except FileNotFoundError:
        logger.error(f"Input path does not exist: {input_path}")
        sys.exit(2)
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(2)
    except ValueError as exc:
        logger.error(str(exc))
        sys.exit(2)
    logger.info("Processing single file input" if input_path.is_file() else "Processing directory input")

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


def cli() -> None:
    """Run the CLI entry point."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Pipeline interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Pipeline failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli()
