# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Lossless conversion between v2 HTTP schemas and application contracts."""

from __future__ import annotations

from dataclasses import asdict
from enum import Enum

from bijux_canon_runtime.api.v2.schemas import (
    AnswerPolicy,
    Budget,
    JobStatusResponse,
    RequestContext,
)
from bijux_canon_runtime.model.execution.request_plan import (
    ExecutionProfile,
    RetrievalFilters,
    RuntimeOperationRequest,
    RuntimeOutputPolicy,
    RuntimeRequestBudget,
    RuntimeRequestOperation,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, RequestID
from bijux_canon_runtime.ontology.public import ReplayMode
from bijux_canon_runtime.runtime.execution.durable_jobs import DurableJobSnapshot


def operation_request(
    *,
    context: RequestContext,
    operation: RuntimeRequestOperation,
    execution_profile: str,
    budget: Budget,
    scope: str,
    query: str | None = None,
    source_directory: str | None = None,
    corpus_id: str | None = None,
    index_id: str | None = None,
    filters: tuple[tuple[str, ...], tuple[str, ...]] = ((), ()),
    top_k: int | None = None,
    answer_policy: AnswerPolicy | None = None,
) -> RuntimeOperationRequest:
    """Construct the exact typed request consumed by all application transports."""
    return RuntimeOperationRequest(
        request_id=RequestID(context.request_id),
        operation=operation,
        execution_profile=ExecutionProfile(execution_profile),
        budget=RuntimeRequestBudget(
            timeout_seconds=budget.timeout_seconds,
            max_artifact_bytes=budget.max_artifact_bytes,
            max_steps=budget.max_steps,
            max_provider_tokens=budget.max_provider_tokens,
        ),
        replay_mode=ReplayMode(context.replay_mode),
        scope=scope,
        query=query,
        source_directory=source_directory,
        corpus_id=None if corpus_id is None else ArtifactID(corpus_id),
        index_id=None if index_id is None else ArtifactID(index_id),
        filters=RetrievalFilters(
            document_ids=filters[0],
            source_uris=filters[1],
        ),
        top_k=top_k,
        provider=None if answer_policy is None else answer_policy.provider,
        output_policy=(
            None
            if answer_policy is None
            else RuntimeOutputPolicy(
                require_citations=answer_policy.require_citations,
                permit_insufficient_answer=answer_policy.permit_insufficient_answer,
                publish=answer_policy.publish,
            )
        ),
    )


def job_status(snapshot: DurableJobSnapshot) -> JobStatusResponse:
    """Render durable authority state without inventing run or attempt identity."""
    base = f"/api/v2/jobs/{snapshot.job_id}"
    return JobStatusResponse(
        schema_version="bijux.runtime.http-job-status.v2",
        job_id=snapshot.job_id,
        kind=snapshot.kind.value,
        status=snapshot.status.value,
        cancel_requested=snapshot.cancel_requested,
        attempt_count=snapshot.attempt_count,
        submitted_at=snapshot.submitted_at,
        started_at=snapshot.started_at,
        finished_at=snapshot.finished_at,
        deadline_at=snapshot.deadline_at,
        timeout_seconds=snapshot.timeout_seconds,
        result_available=snapshot.result is not None,
        error_type=snapshot.error_type,
        error_message=snapshot.error_message,
        status_uri=base,
        result_uri=f"{base}/result",
        cancellation_uri=f"{base}/cancellation",
    )


def json_value(value: object) -> object:
    """Convert typed persisted models to JSON-compatible values."""
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return json_value(asdict(value))  # type: ignore[call-overload]
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [json_value(item) for item in value]
    return value


__all__ = ["job_status", "json_value", "operation_request"]
