# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Runtime helpers for API support."""

from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException

from bijux_canon_index.application.engine import VectorExecutionEngine
from bijux_canon_index.core.config import (
    EmbeddingCacheConfig,
    EmbeddingConfig,
    ExecutionConfig,
    VectorStoreConfig,
)
from bijux_canon_index.core.errors import BijuxError
from bijux_canon_index.core.runtime.vector_execution import RandomnessProfile
from bijux_canon_index.core.types import ExecutionBudget
from bijux_canon_index.interfaces.errors import (
    is_refusal,
    refusal_payload,
    to_http_status,
)
from bijux_canon_index.interfaces.errors.reporting import record_failure
from bijux_canon_index.interfaces.schemas.requests import ExecutionRequestPayload

REFUSAL_EXAMPLE = {
    "error": {
        "reason": "determinism_violation",
        "message": "[INV-000] Deterministic execution requires a deterministic vector store",
        "remediation": "Use deterministic inputs or switch to non_deterministic contract with declared randomness.",
    }
}


def raise_http_error(exc: BijuxError, correlation_id: str | None = None) -> NoReturn:
    """Raise HTTP error."""
    record_failure(exc)
    detail: object
    if is_refusal(exc):
        detail = {"error": refusal_payload(exc)}
    else:
        detail = {"message": str(exc)}
    headers = {"X-Correlation-Id": correlation_id} if correlation_id else None
    raise HTTPException(
        status_code=to_http_status(exc), detail=detail, headers=headers
    ) from None


def config_from_payload(
    *,
    vector_store: str | None = None,
    vector_store_uri: str | None = None,
    vector_store_options: dict[str, str] | None = None,
    embed_provider: str | None = None,
    embed_model: str | None = None,
    cache_embeddings: str | None = None,
) -> ExecutionConfig:
    """Handle config from payload."""
    vs_cfg = None
    if vector_store:
        vs_cfg = VectorStoreConfig(
            backend=vector_store,
            uri=vector_store_uri,
            options=vector_store_options,
        )
    embed_cfg = None
    if embed_provider or embed_model or cache_embeddings:
        cache_cfg = (
            EmbeddingCacheConfig(backend=None, uri=cache_embeddings)
            if cache_embeddings
            else None
        )
        embed_cfg = EmbeddingConfig(
            provider=embed_provider,
            model=embed_model,
            cache=cache_cfg,
        )
    return ExecutionConfig(vector_store=vs_cfg, embeddings=embed_cfg)


def engine_from_payload(
    *,
    vector_store: str | None = None,
    vector_store_uri: str | None = None,
    vector_store_options: dict[str, str] | None = None,
    embed_provider: str | None = None,
    embed_model: str | None = None,
    cache_embeddings: str | None = None,
) -> VectorExecutionEngine:
    """Handle engine from payload."""
    return VectorExecutionEngine(
        config=config_from_payload(
            vector_store=vector_store,
            vector_store_uri=vector_store_uri,
            vector_store_options=vector_store_options,
            embed_provider=embed_provider,
            embed_model=embed_model,
            cache_embeddings=cache_embeddings,
        )
    )


def replay_inputs_from_request(
    req: ExecutionRequestPayload,
) -> tuple[str, RandomnessProfile | None, ExecutionBudget | None]:
    """Handle replay inputs from request."""
    randomness_profile = None
    if req.randomness_profile is not None:
        randomness_profile = RandomnessProfile(
            seed=req.randomness_profile.seed,
            sources=tuple(req.randomness_profile.sources or ()),
            bounded=req.randomness_profile.bounded,
            non_replayable=req.randomness_profile.non_replayable,
        )
    execution_budget = None
    if req.execution_budget is not None:
        execution_budget = ExecutionBudget(
            max_latency_ms=req.execution_budget.max_latency_ms,
            max_memory_mb=req.execution_budget.max_memory_mb,
            max_error=req.execution_budget.max_error,
        )
    return (req.request_text or "", randomness_profile, execution_budget)


__all__ = [
    "REFUSAL_EXAMPLE",
    "config_from_payload",
    "engine_from_payload",
    "raise_http_error",
    "replay_inputs_from_request",
]
