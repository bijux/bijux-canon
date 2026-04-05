# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
from typing import TypeAlias

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from bijux_canon_reason.api.v1.openapi_models import ErrorDetail
from bijux_canon_reason.application.run_artifacts import RunBuilder, RunInputs
from bijux_canon_reason.core.types import Plan, ProblemSpec
from bijux_canon_reason.interfaces.access_guards import sanitize_run_id
from bijux_canon_reason.interfaces.serialization.json_file import (
    read_json_file,
    write_json_file,
)
from bijux_canon_reason.interfaces.serialization.trace_jsonl import read_trace_jsonl
from bijux_canon_reason.traces.replay import replay_from_artifacts
from bijux_canon_reason.verification.verifier import verify_trace

JsonDocument: TypeAlias = (
    dict[str, object] | list[object] | str | int | float | bool | None
)


class RunCreateRequest(BaseModel):
    spec: ProblemSpec
    preset: str = Field(default="default")
    seed: int = Field(default=0, ge=0)


class RunCreateResponse(BaseModel):
    run_id: str
    run_dir: str
    trace_id: str
    fingerprint: str


class RunReplayResponse(BaseModel):
    original_trace_fingerprint: str
    replayed_trace_fingerprint: str
    diff_summary: dict[str, object]
    replay_trace_path: str


def register_run_routes(
    app: FastAPI,
    *,
    artifacts_dir: Path,
    guard_request: Callable[[Request], None],
    max_request_bytes: int,
) -> None:
    guard_responses = {
        401: {
            "description": "Authentication failed for the requested endpoint.",
            "model": ErrorDetail,
        },
        413: {
            "description": "The request or response exceeded the configured size limit.",
            "model": ErrorDetail,
        },
        415: {
            "description": "The submitted content type is not accepted by the API.",
            "model": ErrorDetail,
        },
        429: {
            "description": "The caller exceeded the configured rate limit.",
            "model": ErrorDetail,
        },
    }

    @app.post(
        "/v1/runs",
        response_model=RunCreateResponse,
        tags=["Runs"],
        summary="Create a run",
        description=(
            "Build a deterministic run directory from the submitted problem spec and "
            "return the identifiers needed to inspect, verify, or replay it later."
        ),
        operation_id="createReasonRun",
        responses={
            **guard_responses,
            422: {
                "description": "Validation failed for the run creation payload.",
                "model": ErrorDetail,
            },
        },
    )
    def create_run(req: RunCreateRequest, request: Request) -> RunCreateResponse:
        guard_request(request)
        artifacts = RunBuilder().build(
            inputs=RunInputs(spec=req.spec, preset=req.preset, seed=req.seed),
            artifacts_root=artifacts_dir,
        )
        fingerprint = artifacts.fingerprint_path.read_text(encoding="utf-8").strip()
        return RunCreateResponse(
            run_id=artifacts.run_id,
            run_dir=str(artifacts.run_dir),
            trace_id=artifacts.trace.id,
            fingerprint=fingerprint,
        )

    @app.get(
        "/v1/runs/{run_id}",
        response_model=dict[str, object],
        tags=["Runs"],
        summary="Get run metadata",
        description="Return the stored run metadata document for a previously created run.",
        operation_id="getReasonRun",
        responses={
            **guard_responses,
            404: {
                "description": "The requested run was not found.",
                "model": ErrorDetail,
            },
        },
    )
    def get_run(run_id: str, request: Request) -> JsonDocument:
        guard_request(request)
        return _load_run_document(
            artifacts_dir=artifacts_dir,
            run_id=run_id,
            filename="run_meta.json",
            missing_detail="run not found",
        )

    @app.get(
        "/v1/runs/{run_id}/manifest",
        response_model=dict[str, object],
        tags=["Runs"],
        summary="Get run manifest",
        description="Return the persisted manifest document for a previously created run.",
        operation_id="getReasonRunManifest",
        responses={
            **guard_responses,
            404: {
                "description": "The requested manifest was not found.",
                "model": ErrorDetail,
            },
        },
    )
    def get_manifest(run_id: str, request: Request) -> JsonDocument:
        guard_request(request)
        return _load_run_document(
            artifacts_dir=artifacts_dir,
            run_id=run_id,
            filename="manifest.json",
            missing_detail="manifest not found",
        )

    @app.get(
        "/v1/runs/{run_id}/trace",
        response_class=PlainTextResponse,
        tags=["Runs"],
        summary="Get run trace",
        description="Return the recorded trace for a run as newline-delimited JSON.",
        operation_id="getReasonRunTrace",
        responses={
            **guard_responses,
            404: {
                "description": "The requested trace was not found.",
                "content": {
                    "application/json": {
                        "schema": ErrorDetail.model_json_schema(),
                    }
                },
            },
        },
    )
    def fetch_trace(run_id: str, request: Request) -> str:
        guard_request(request)
        path = _run_dir(artifacts_dir, run_id) / "trace.jsonl"
        if not path.exists():
            raise HTTPException(status_code=404, detail="trace not found")
        return _read_trace_content(path=path, max_request_bytes=max_request_bytes)

    @app.post(
        "/v1/runs/{run_id}/verify",
        response_model=dict[str, object],
        tags=["Runs"],
        summary="Verify a run",
        description="Verify a stored run trace against its persisted plan and return the verification report.",
        operation_id="verifyReasonRun",
        responses={
            **guard_responses,
            404: {
                "description": "Required run artifacts were not found.",
                "model": ErrorDetail,
            },
        },
    )
    def verify_run(run_id: str, request: Request) -> dict[str, object]:
        guard_request(request)
        run_dir = _run_dir(artifacts_dir, run_id)
        trace_path = run_dir / "trace.jsonl"
        plan_path = run_dir / "plan.json"
        if not trace_path.exists() or not plan_path.exists():
            raise HTTPException(status_code=404, detail="run artifacts missing")

        trace = read_trace_jsonl(trace_path)
        plan = Plan.model_validate(read_json_file(plan_path))
        report = verify_trace(trace=trace, plan=plan, artifacts_dir=run_dir)

        output_path = run_dir / "verify.verify.json"
        write_json_file(output_path, report.model_dump(mode="json"))
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {"report": payload}

    @app.post(
        "/v1/runs/{run_id}/replay",
        response_model=RunReplayResponse,
        tags=["Runs"],
        summary="Replay a run",
        description="Replay a stored run trace and report the resulting fingerprint comparison.",
        operation_id="replayReasonRun",
        responses={
            **guard_responses,
            404: {
                "description": "The requested trace was not found.",
                "model": ErrorDetail,
            },
        },
    )
    def replay_run(run_id: str, request: Request) -> RunReplayResponse:
        guard_request(request)
        trace_path = _run_dir(artifacts_dir, run_id) / "trace.jsonl"
        if not trace_path.exists():
            raise HTTPException(status_code=404, detail="trace not found")
        result, replay_trace_path = replay_from_artifacts(trace_path)
        return RunReplayResponse(
            original_trace_fingerprint=result.original_trace_fingerprint,
            replayed_trace_fingerprint=result.replayed_trace_fingerprint,
            diff_summary=result.diff_summary,
            replay_trace_path=str(replay_trace_path),
        )


def _run_dir(artifacts_dir: Path, run_id: str) -> Path:
    try:
        sanitized_run_id = sanitize_run_id(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
    return artifacts_dir / "runs" / sanitized_run_id


def _load_run_document(
    *,
    artifacts_dir: Path,
    run_id: str,
    filename: str,
    missing_detail: str,
) -> JsonDocument:
    path = _run_dir(artifacts_dir, run_id) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=missing_detail)
    return _unwrap_canonical_document(read_json_file(path))


def _unwrap_canonical_document(raw: object) -> JsonDocument:
    if isinstance(raw, dict) and "data" in raw and "canonical_version" in raw:
        return raw["data"]
    if isinstance(raw, (dict, list, str, int, float, bool)) or raw is None:
        return raw
    return str(raw)


def _read_trace_content(*, path: Path, max_request_bytes: int) -> str:
    content = path.read_text(encoding="utf-8")
    if len(content.encode("utf-8")) > max_request_bytes * 10:
        raise HTTPException(status_code=413, detail="response too large")
    return content


__all__ = [
    "RunCreateRequest",
    "RunCreateResponse",
    "RunReplayResponse",
    "register_run_routes",
]
