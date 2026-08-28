"""API v1 request handlers."""

from __future__ import annotations

from pathlib import Path

from bijux_canon_agent.api.v1.errors import HTTP_STATUS_BY_CODE, APIErrorCode
from bijux_canon_agent.api.v1.schemas import (
    ErrorResponseV1,
    RunRequestV1,
    RunResponseV1,
)
from bijux_canon_agent.application.execution_service import run_offline_agent


def _error_response(code: APIErrorCode, message: str) -> ErrorResponseV1:
    return ErrorResponseV1(
        code=code.value,
        message=message,
        http_status=HTTP_STATUS_BY_CODE[code],
    )


def run_pipeline_v1(request: RunRequestV1) -> RunResponseV1:
    """
    Run the canonical pipeline for API v1.

    This endpoint provides deterministic, offline-only execution using a fixed configuration.
    """
    outcome = run_offline_agent(
        context_id=request.context_id,
        text=request.text,
        task_goal=request.task_goal,
        working_root=Path.cwd(),
    )
    error = None
    if outcome.error_kind is not None:
        error = _error_response(
            APIErrorCode(outcome.error_kind),
            outcome.error_message or outcome.error_kind,
        )
    return RunResponseV1(
        success=outcome.success,
        context_id=outcome.context_id,
        error=error,
        result=outcome.result,
    )
