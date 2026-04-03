"""API v1 request/response schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RunConfigV1(BaseModel):
    """Deterministic config overrides accepted by the HTTP API."""

    model_config = ConfigDict(extra="allow")

    agents: (
        list[
            Literal[
                "file_reader", "summarizer", "validator", "critique", "task_handler"
            ]
        ]
        | None
    ) = None
    strategy: Literal["extractive"] | None = None
    backend: Literal["simple"] | None = None


class RunRequestV1(BaseModel):
    """Input for running the canonical pipeline."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(
        ...,
        min_length=1,
        max_length=200000,
        description="Input text to process.",
    )
    task_goal: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Goal or task description for the pipeline.",
    )
    context_id: str = Field(
        "api-v1",
        min_length=1,
        max_length=128,
        description="Identifier for the execution context.",
    )
    config: RunConfigV1 | None = None


class ErrorResponseV1(BaseModel):
    """Structured error response for API consumers."""

    code: str
    message: str
    http_status: int


class TraceMetadata(BaseModel):
    """Trace metadata returned alongside API responses."""

    run_id: str | None = None
    trace_schema_version: str | None = None


class RunResponseV1(BaseModel):
    """Output from running the canonical pipeline."""

    success: bool
    context_id: str
    result: dict[str, Any] | None = None
    error: ErrorResponseV1 | None = None
    trace_metadata: TraceMetadata | None = None
