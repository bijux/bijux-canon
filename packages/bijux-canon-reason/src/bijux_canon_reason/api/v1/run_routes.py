# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Run routes helpers for API support."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi import Path as FastPath
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, StringConstraints, field_validator

from bijux_canon_reason.api.v1.openapi_models import ErrorDetail
from bijux_canon_reason.application.run_service import (
    JsonDocument,
    RunNotFoundError,
    RunResponseTooLargeError,
    RunService,
)
from bijux_canon_reason.core.types import ProblemSpec

RUN_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$"
RunIdPath = Annotated[str, StringConstraints(pattern=RUN_ID_PATTERN), FastPath()]


class RunCreateRequest(BaseModel):
    """Represents run create request."""

    spec: ProblemSpec
    preset: str = Field(default="default")
    seed: int = Field(default=0, ge=0)

    @field_validator("seed", mode="before")
    @classmethod
    def _reject_boolean_seed(cls, value: object) -> object:
        """Reject booleans while still allowing numeric JSON integers."""
        if isinstance(value, bool):
            raise ValueError("seed must not be a boolean")
        return value


class RunCreateResponse(BaseModel):
    """Represents run create response."""

    run_id: str
    run_dir: str
    trace_id: str
    fingerprint: str


class RunReplayResponse(BaseModel):
    """Represents run replay response."""

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
    """Register run routes."""
    service = RunService(
        artifacts_dir=artifacts_dir,
        max_request_bytes=max_request_bytes,
    )
    guard_responses: dict[int | str, dict[str, Any]] = {
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
            400: {
                "description": "The submitted request body could not be parsed as JSON.",
                "model": ErrorDetail,
            },
            422: {
                "description": "Validation failed for the run creation payload.",
                "model": ErrorDetail,
            },
        },
    )
    def create_run(req: RunCreateRequest, request: Request) -> RunCreateResponse:
        """Create run."""
        guard_request(request)
        return RunCreateResponse.model_validate(
            service.create_run(spec=req.spec, preset=req.preset, seed=req.seed)
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
            422: {
                "description": "Validation failed for the requested run id.",
                "model": ErrorDetail,
            },
        },
    )
    def get_run(
        request: Request,
        run_id: RunIdPath,
    ) -> JsonDocument:
        """Return run."""
        guard_request(request)
        try:
            return service.get_document(run_id=run_id, filename="run_meta.json")
        except RunNotFoundError as exc:
            raise HTTPException(status_code=404, detail="run not found") from exc

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
            422: {
                "description": "Validation failed for the requested run id.",
                "model": ErrorDetail,
            },
        },
    )
    def get_manifest(
        request: Request,
        run_id: RunIdPath,
    ) -> JsonDocument:
        """Return manifest."""
        guard_request(request)
        try:
            return service.get_document(run_id=run_id, filename="manifest.json")
        except RunNotFoundError as exc:
            raise HTTPException(status_code=404, detail="manifest not found") from exc

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
            422: {
                "description": "Validation failed for the requested run id.",
                "model": ErrorDetail,
            },
        },
    )
    def fetch_trace(
        request: Request,
        run_id: RunIdPath,
    ) -> str:
        """Handle fetch trace."""
        guard_request(request)
        try:
            return service.get_trace(run_id=run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=404, detail="trace not found") from exc
        except RunResponseTooLargeError as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc

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
            422: {
                "description": "Validation failed for the requested run id.",
                "model": ErrorDetail,
            },
        },
    )
    def verify_run(
        request: Request,
        run_id: RunIdPath,
    ) -> dict[str, object]:
        """Handle verify run."""
        guard_request(request)
        try:
            return service.verify_run(run_id=run_id)
        except RunNotFoundError as exc:
            raise HTTPException(
                status_code=404, detail="run artifacts missing"
            ) from exc

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
            422: {
                "description": "Validation failed for the requested run id.",
                "model": ErrorDetail,
            },
        },
    )
    def replay_run(
        request: Request,
        run_id: RunIdPath,
    ) -> RunReplayResponse:
        """Handle replay run."""
        guard_request(request)
        try:
            return RunReplayResponse.model_validate(service.replay_run(run_id=run_id))
        except RunNotFoundError as exc:
            raise HTTPException(status_code=404, detail="trace not found") from exc


__all__ = [
    "RunCreateRequest",
    "RunCreateResponse",
    "RunReplayResponse",
    "register_run_routes",
]
