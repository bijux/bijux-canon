"""API v1 request handlers."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any

from bijux_agent.api.v1.errors import HTTP_STATUS_BY_CODE, APIErrorCode
from bijux_agent.api.v1.schemas import ErrorResponseV1, RunRequestV1, RunResponseV1
from bijux_agent.pipeline.canonical import AuditableDocPipeline
from bijux_agent.pipeline.termination import ExecutionTerminationReason
from bijux_agent.utilities.logger_manager import LoggerConfig, LoggerManager

_DEFAULT_AGENTS: list[str] = [
    "file_reader",
    "summarizer",
    "validator",
    "critique",
    "task_handler",
]


def _error_response(code: APIErrorCode, message: str) -> ErrorResponseV1:
    return ErrorResponseV1(
        code=code.value,
        message=message,
        http_status=HTTP_STATUS_BY_CODE[code],
    )


def _build_context(request: RunRequestV1) -> dict[str, Any]:
    inputs_dir = Path.cwd() / "artifacts" / "api" / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(
        request.context_id.encode("utf-8", errors="replace")
    ).hexdigest()
    input_path = inputs_dir / f"context-{digest}.txt"
    input_path.write_text(request.text, encoding="utf-8")
    return {
        "context_id": request.context_id,
        "text": request.text,
        "task_goal": request.task_goal,
        "file_path": str(input_path),
    }


def run_pipeline_v1(request: RunRequestV1) -> RunResponseV1:
    """
    Run the canonical pipeline for API v1.

    This endpoint provides deterministic, offline-only execution using a fixed configuration.
    """
    api_root = Path.cwd() / "artifacts" / "api"
    logger_manager = LoggerManager(LoggerConfig(log_dir=api_root / "logs"))

    # Fixed deterministic configuration (no client overrides)
    resolved_config: dict[str, Any] = {
        "backend": "simple",
        "strategy": "extractive",
        "agents": _DEFAULT_AGENTS,
    }

    try:
        pipeline = AuditableDocPipeline(
            resolved_config,
            logger_manager,
            results_dir=str(api_root / "results"),
        )
        result = asyncio.run(pipeline.run(_build_context(request)))
    except Exception as exc:  # Defensive handling of unexpected errors
        return RunResponseV1(
            success=False,
            context_id=request.context_id,
            error=_error_response(APIErrorCode.INTERNAL_ERROR, str(exc)),
        )

    final_status = result.get("final_status", {})
    termination = final_status.get("termination_reason")

    if termination == ExecutionTerminationReason.FAILURE:
        return RunResponseV1(
            success=False,
            context_id=request.context_id,
            error=_error_response(APIErrorCode.EXECUTION_FAILED, "execution failed"),
            result=result,
        )

    if termination == ExecutionTerminationReason.CONVERGENCE and not final_status.get(
        "converged", False
    ):
        return RunResponseV1(
            success=False,
            context_id=request.context_id,
            error=_error_response(
                APIErrorCode.CONVERGENCE_FAILED, "convergence not reached"
            ),
            result=result,
        )

    return RunResponseV1(success=True, context_id=request.context_id, result=result)
