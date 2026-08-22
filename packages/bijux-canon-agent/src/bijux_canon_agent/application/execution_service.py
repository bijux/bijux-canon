"""Application services shared by agent transports."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
from pathlib import Path
import time
from typing import Any

from bijux_canon_agent.observability.logging import LoggerConfig, LoggerManager
from bijux_canon_agent.pipeline.canonical import AuditableDocPipeline
from bijux_canon_agent.pipeline.termination import ExecutionTerminationReason

_DEFAULT_AGENTS: list[str] = [
    "file_reader",
    "summarizer",
    "validator",
    "critique",
    "stage_runner",
]


@dataclass(frozen=True)
class AgentRunOutcome:
    """Transport-neutral result of one bounded agent run."""

    success: bool
    context_id: str
    result: dict[str, Any] | None = None
    error_kind: str | None = None
    error_message: str | None = None


def run_offline_agent(
    *, context_id: str, text: str, task_goal: str, working_root: Path
) -> AgentRunOutcome:
    """Run the fixed deterministic API profile and classify its outcome."""
    api_root = working_root / "artifacts" / "api"
    inputs_dir = api_root / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(context_id.encode("utf-8", errors="replace")).hexdigest()
    input_path = inputs_dir / f"context-{digest}.txt"
    input_path.write_text(text, encoding="utf-8")
    context = {
        "context_id": context_id,
        "text": text,
        "task_goal": task_goal,
        "file_path": str(input_path),
    }
    logger_manager = LoggerManager(LoggerConfig(log_dir=api_root / "logs"))
    config: dict[str, Any] = {
        "backend": "simple",
        "strategy": "extractive",
        "agents": _DEFAULT_AGENTS,
    }
    try:
        pipeline = AuditableDocPipeline(
            config,
            logger_manager,
            results_dir=str(api_root / "results"),
        )
        result = asyncio.run(pipeline.run(context))
    except Exception as exc:  # pragma: no cover - defensive transport mapping
        return AgentRunOutcome(
            success=False,
            context_id=context_id,
            error_kind="INTERNAL_ERROR",
            error_message=str(exc),
        )
    final_status = result.get("final_status", {})
    termination = final_status.get("termination_reason")
    if termination == ExecutionTerminationReason.FAILURE:
        return AgentRunOutcome(
            success=False,
            context_id=context_id,
            result=result,
            error_kind="EXECUTION_FAILED",
            error_message="execution failed",
        )
    if termination == ExecutionTerminationReason.CONVERGENCE and not final_status.get(
        "converged", False
    ):
        return AgentRunOutcome(
            success=False,
            context_id=context_id,
            result=result,
            error_kind="CONVERGENCE_FAILED",
            error_message="convergence not reached",
        )
    return AgentRunOutcome(success=True, context_id=context_id, result=result)


async def process_input_files(
    *,
    pipeline: AuditableDocPipeline,
    files: list[Path],
    task_goal: str,
    logger: Any,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute the pipeline across admitted files and collect typed run buckets."""
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
    results: dict[str, Any] = {"successful": [], "failed": [], "telemetry": {}}
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


def create_agent_pipeline(
    *, config: dict[str, Any], logger_manager: LoggerManager, results_dir: Path
) -> AuditableDocPipeline:
    """Construct the concrete agent pipeline at the application boundary."""
    return AuditableDocPipeline(
        config=config,
        logger_manager=logger_manager,
        results_dir=str(results_dir),
    )


__all__ = [
    "AgentRunOutcome",
    "create_agent_pipeline",
    "process_input_files",
    "run_offline_agent",
]
