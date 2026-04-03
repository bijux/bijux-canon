"""API v1 contract tests."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError
import pytest

from bijux_agent.api.v1.errors import HTTP_STATUS_BY_CODE, APIErrorCode
from bijux_agent.api.v1.handlers import run_pipeline_v1
from bijux_agent.api.v1.schemas import RunRequestV1
from bijux_agent.httpapi import create_app
from bijux_agent.utilities.version import get_runtime_version


def test_schema_validation() -> None:
    RunRequestV1(text="hello", task_goal="summarize")
    try:
        RunRequestV1(text="", task_goal="summarize")
    except ValidationError:
        pass
    else:
        raise AssertionError("Empty text should fail validation")


def test_handler_determinism() -> None:
    request = RunRequestV1(text="Minimal input.", task_goal="summarize")
    first = run_pipeline_v1(request)
    second = run_pipeline_v1(request)
    assert first.success == second.success
    if first.error or second.error:
        assert first.error is not None
        assert second.error is not None
        assert first.error.code == second.error.code
        assert first.error.http_status == second.error.http_status
        return
    assert first.result is not None
    assert second.result is not None
    assert first.result.get("final_status") == second.result.get("final_status")
    assert first.result.get("execution_path") == second.result.get("execution_path")
    assert set(first.result.get("stages", {}).keys()) == set(
        second.result.get("stages", {}).keys()
    )


def test_error_mapping() -> None:
    assert HTTP_STATUS_BY_CODE[APIErrorCode.VALIDATION_ERROR] == 400
    assert HTTP_STATUS_BY_CODE[APIErrorCode.EXECUTION_FAILED] == 422
    assert HTTP_STATUS_BY_CODE[APIErrorCode.CONVERGENCE_FAILED] == 422
    assert HTTP_STATUS_BY_CODE[APIErrorCode.INTERNAL_ERROR] == 500


@pytest.mark.asyncio
async def test_health_endpoint_reports_status_and_version() -> None:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/v1/health",
    }
    body = b""
    received = False

    async def receive() -> dict[str, Any]:
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    responses: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        responses.append(message)

    app = create_app()
    await app(scope, receive, send)
    start = next(msg for msg in responses if msg["type"] == "http.response.start")
    body_msg = next(msg for msg in responses if msg["type"] == "http.response.body")

    assert start["status"] == 200
    payload = json.loads(body_msg["body"].decode("utf-8"))
    assert payload["status"] == "ok"
    assert payload["version"] == get_runtime_version()
