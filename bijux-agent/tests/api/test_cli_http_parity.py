# SPDX-FileCopyrightText: Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
"""Smoke test verifying CLI and HTTP outputs stay in sync."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import asdict
from datetime import UTC
from datetime import datetime as real_datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
import uuid

from _pytest.monkeypatch import MonkeyPatch
from tests.utils.trace_helpers import default_model_metadata
import yaml

from bijux_agent.cli.helpers import build_trace_from_result
from bijux_agent.config.defaults import MINIMAL_REFERENCE_CONFIG
from bijux_agent.enums import DecisionOutcome
from bijux_agent.httpapi import create_app
import bijux_agent.main as cli_main

DEFAULT_HTTP_AGENTS = [
    "file_reader",
    "summarizer",
    "validator",
    "critique",
    "task_handler",
]


class FixedDatetime(real_datetime):
    """Deterministic datetime used to keep trace hashes reproducible."""

    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        return real_datetime(2025, 1, 1, tzinfo=UTC)


def _resolved_http_config(request_config: Mapping[str, Any] | None) -> dict[str, Any]:
    resolved = dict(MINIMAL_REFERENCE_CONFIG)
    if request_config:
        resolved.update(request_config)
    if request_config and "agents" in request_config:
        resolved["agents"] = request_config["agents"]
    else:
        resolved["agents"] = DEFAULT_HTTP_AGENTS
    resolved.setdefault("strategy", "extractive")
    resolved.setdefault("backend", "simple")
    resolved["model_metadata"] = asdict(default_model_metadata())
    return resolved


def _trace_hash_from_result(
    pipeline_result: dict[str, Any],
    file_path: str,
    task_goal: str,
    config: Mapping[str, Any],
    trace_dir: Path,
) -> str:
    normalized_result = dict(pipeline_result)
    if "stages" in normalized_result:
        normalized_result["stages"] = _scrub_stage_audits(normalized_result["stages"])
    if "result" in normalized_result:
        normalized_result["result"] = _strip_audit_fields(normalized_result["result"])
    final_status = pipeline_result["final_status"]
    success = bool(final_status.get("success"))
    verdict = DecisionOutcome.PASS if success else DecisionOutcome.VETO
    confidence = float(final_status.get("score", 0.0))
    convergence_hash = final_status.get("convergence_hash")
    convergence_reason = final_status.get("convergence_reason")
    termination_reason = final_status.get("termination_reason")
    trace_dir.mkdir(parents=True, exist_ok=True)
    _, trace = build_trace_from_result(
        pipeline_result=normalized_result,
        file_path=file_path,
        task_goal=task_goal,
        config=config,
        verdict=verdict,
        confidence=confidence,
        trace_dir=trace_dir,
        convergence_hash=convergence_hash,
        convergence_reason=convergence_reason,
        termination_reason=termination_reason,
    )
    serialized = json.dumps(trace.to_dict(), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _scrub_stage_audits(stages: Mapping[str, Any]) -> dict[str, Any]:
    scrubbed: dict[str, Any] = {}
    for key, value in stages.items():
        scrubbed[key] = _strip_audit_fields(value)
    return scrubbed


def _strip_audit_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_audit_fields(val)
            for key, val in value.items()
            if key
            not in {
                "timestamp",
                "duration_sec",
                "started_at",
                "ended_at",
                "confidence",
            }
        }
    if isinstance(value, list):
        return [_strip_audit_fields(item) for item in value]
    return value


def _http_input_path(context_id: str) -> Path:
    digest = hashlib.sha256(context_id.encode("utf-8", errors="replace")).hexdigest()
    return Path.cwd() / "artifacts" / "api" / "inputs" / f"context-{digest}.txt"


async def _send_http_run(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    scope = {"type": "http", "method": "POST", "path": "/v1/run"}
    body = json.dumps(payload).encode("utf-8")
    pending = True

    async def receive() -> dict[str, Any]:
        nonlocal pending
        if pending:
            pending = False
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    responses: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        responses.append(message)

    app = create_app()
    await app(scope, receive, send)

    start = next(msg for msg in responses if msg["type"] == "http.response.start")
    body_message = next(msg for msg in responses if msg["type"] == "http.response.body")
    return start["status"], json.loads(body_message["body"].decode("utf-8"))


def test_cli_http_parity(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    for key in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "HUGGINGFACE_API_KEY",
        "DEEPSEEK_API_KEY",
    ):
        monkeypatch.setenv(key, "test")

    text = "CLI vs HTTP parity smoke text"
    task_goal = "parity-smoke-test"
    context_id = "parity-http"
    cli_config = {
        "task_goal": task_goal,
        "backend": "simple",
        "strategy": "extractive",
        "agents": ["file_reader", "task_handler"],
        "pipeline": {"parameters": {"stage_timeout": 15}},
        "logging": {
            "log_dir": str(tmp_path / "logs"),
            "log_level": "INFO",
            "structured_logging": False,
            "async_logging": False,
            "telemetry_enabled": False,
        },
        "output": {
            "output_dir": str(tmp_path / "cli-output"),
            "output_format": "json",
        },
        "model_metadata": asdict(default_model_metadata()),
    }
    config_path = tmp_path / "cli-config.yml"
    config_path.write_text(yaml.safe_dump(cli_config), encoding="utf-8")

    input_file = _http_input_path(context_id)
    inputs_dir = input_file.parent
    inputs_dir.mkdir(parents=True, exist_ok=True)
    input_file.write_text(text, encoding="utf-8")
    results_dir = tmp_path / "cli-results"
    results_dir.mkdir(parents=True, exist_ok=True)

    captured: dict[str, Any] = {}

    original_write = cli_main.write_final_artifacts

    def capture_write_final_artifacts(*args: Any, **kwargs: Any) -> Path:
        captured["success_entry"] = kwargs.get("success_entry")
        captured["results"] = kwargs.get("results")
        captured["config"] = kwargs.get("config")
        captured["task_goal"] = kwargs.get("task_goal")
        return original_write(*args, **kwargs)

    monkeypatch.setattr(
        cli_main, "write_final_artifacts", capture_write_final_artifacts
    )

    async def patched_validate(
        self, result: Any, task_goal: str, context_id: str | None = None
    ) -> dict[str, Any]:
        return {"is_valid": True, "issues": []}

    monkeypatch.setattr(
        "bijux_agent.pipeline.results.results.PipelineResultsMixin._validate_final_result",
        patched_validate,
    )
    monkeypatch.setattr("bijux_agent.cli.helpers.datetime", FixedDatetime)
    monkeypatch.setattr(
        "bijux_agent.cli.helpers.uuid.uuid4",
        lambda: uuid.UUID(int=0),
    )

    cli_args = [
        "bijux-agent",
        "run",
        str(input_file),
        "--out",
        str(results_dir),
        "--config",
        str(config_path),
    ]
    monkeypatch.setattr(sys, "argv", cli_args)

    asyncio.run(cli_main.main())

    success_entry = captured.get("success_entry")
    assert success_entry, "CLI run did not produce a primary success entry"
    cli_result = success_entry["result"]
    cli_final_status = cli_result["final_status"]
    cli_trace_hash = _trace_hash_from_result(
        cli_result,
        str(input_file),
        task_goal,
        cli_config,
        trace_dir=tmp_path / "cli-trace",
    )

    http_request_config = dict(cli_config)
    http_payload = {
        "text": text,
        "task_goal": task_goal,
        "context_id": context_id,
        "config": http_request_config,
    }
    status, http_response = asyncio.run(_send_http_run(http_payload))
    assert http_response["success"] is True
    http_result = http_response["result"]
    assert http_result is not None
    http_final_status = http_result["final_status"]
    inputs_path = _http_input_path(context_id)
    try:
        http_trace_hash = _trace_hash_from_result(
            http_result,
            str(inputs_path),
            task_goal,
            _resolved_http_config(http_request_config),
            trace_dir=tmp_path / "http-trace",
        )
    finally:
        if inputs_path.exists():
            inputs_path.unlink()
        inputs_dir = _http_input_path(context_id).parent
        with suppress(OSError):
            inputs_dir.rmdir()

    assert cli_final_status == http_final_status
    assert cli_trace_hash == http_trace_hash
