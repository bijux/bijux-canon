"""Compatibility helpers for the Bijux Agent CLI."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import time
from typing import Any
import uuid

from bijux_canon_agent.interfaces.cli import config_support as _config_support_module
from bijux_canon_agent.interfaces.cli import replay_support as _replay_support_module
from bijux_canon_agent.interfaces.cli import (
    result_artifacts as _result_artifacts_module,
)
from bijux_canon_agent.pipeline.canonical import AuditableDocPipeline
from bijux_canon_agent.traces import RunTrace


async def process_files(
    pipeline: AuditableDocPipeline,
    files: list[Path],
    task_goal: str,
    logger: Any,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Process a list of files using the pipeline."""
    if not files:
        logger.warning("No files provided to process")
        return {
            "successful": [],
            "failed": [],
            "telemetry": {
                "total_files": 0,
                "successful": 0,
                "failed": 0,
                "duration_sec": 0,
            },
        }

    logger.info(f"Processing {len(files)} file(s)")
    start_time = time.time()
    results = {"successful": [], "failed": [], "telemetry": {}}

    for input_file in files:
        if not input_file.is_file():
            logger.error(f"Skipping invalid file path: {input_file}")
            results["failed"].append(
                {"file_path": str(input_file), "error": "Not a valid file"}
            )
            continue

        context = {
            "task_goal": task_goal,
            "file_path": str(input_file),
            "context_id": f"file_{input_file.stem}",
        }
        logger.info(f"Processing file: {input_file} with task goal: {task_goal}")

        if dry_run:
            logger.info(f"Dry run: Would process {input_file}")
            results["successful"].append(
                {
                    "file_path": str(input_file),
                    "status": "dry_run",
                    "message": "Dry run completed",
                }
            )
            continue

        try:
            result = await pipeline.run(context)
        except Exception as exc:
            logger.error(
                f"Unexpected error processing {input_file}: {exc}", exc_info=True
            )
            results["failed"].append({"file_path": str(input_file), "error": str(exc)})
            continue

        if "error" in result:
            logger.error(f"Pipeline failed for {input_file}: {result['error']}")
            results["failed"].append(
                {"file_path": str(input_file), "error": result["error"]}
            )
            continue

        results["successful"].append({"file_path": str(input_file), "result": result})

    duration = time.time() - start_time
    results["telemetry"] = {
        "total_files": len(files),
        "successful": len(results["successful"]),
        "failed": len(results["failed"]),
        "duration_sec": duration,
    }
    logger.info(f"Processing completed: {results['telemetry']}")
    return results


def build_trace_from_result(*args: Any, **kwargs: Any) -> tuple[Path, RunTrace]:
    """Build a run trace while preserving helper-level monkeypatch compatibility."""
    _result_artifacts_module.datetime = datetime
    _result_artifacts_module.uuid = uuid
    return _result_artifacts_module.build_trace_from_result(*args, **kwargs)


def write_final_artifacts(*args: Any, **kwargs: Any) -> Path:
    """Write final artifacts through the compatibility helper facade."""
    return _result_artifacts_module.write_final_artifacts(*args, **kwargs)


def load_config(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Load CLI configuration through the compatibility helper facade."""
    return _config_support_module.load_config(*args, **kwargs)


def handle_replay(trace_path: Path) -> None:
    """Replay a stored trace through the compatibility helper facade."""
    _replay_support_module.handle_replay(trace_path)


def load_trace(trace_path: Path) -> RunTrace:
    """Load a stored trace through the compatibility helper facade."""
    return _replay_support_module.load_trace(trace_path)


__all__ = [
    "build_trace_from_result",
    "handle_replay",
    "load_config",
    "load_trace",
    "process_files",
    "write_final_artifacts",
]
