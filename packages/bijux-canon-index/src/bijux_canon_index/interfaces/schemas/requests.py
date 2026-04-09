# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Requests schemas for interface payloads."""

from __future__ import annotations

from typing import Self

from pydantic import Field, model_validator

from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.execution_intent import ExecutionIntent
from bijux_canon_index.core.execution_mode import ExecutionMode
from bijux_canon_index.interfaces.schemas.base import StrictModel


class CreateRequest(StrictModel):
    """Represents create request."""

    name: str = Field(min_length=1)


class IngestRequest(StrictModel):
    """Represents ingest request."""

    documents: list[str]
    vectors: list[list[float]] | None = None
    embed_provider: str | None = None
    embed_model: str | None = None
    cache_embeddings: str | None = None
    correlation_id: str | None = None
    idempotency_key: str | None = None
    vector_store: str | None = None
    vector_store_uri: str | None = None
    vector_store_options: dict[str, str] | None = None

    @model_validator(mode="after")  # type: ignore[untyped-decorator]
    def ensure_lengths(self) -> Self:
        """Ensure lengths."""
        if self.vectors:
            if len(self.documents) != len(self.vectors):
                raise ValueError("documents and vectors length mismatch")
        else:
            if not self.embed_model:
                raise ValueError("embed_model required when vectors are omitted")
        return self


class ExecutionBudgetPayload(StrictModel):
    """Represents execution budget payload."""

    max_latency_ms: int | None = None
    max_memory_mb: int | None = None
    max_error: float | None = None


class RandomnessProfilePayload(StrictModel):
    """Represents randomness profile payload."""

    seed: int | None = None
    sources: list[str] | None = None
    bounded: bool = False
    non_replayable: bool = False


class ExecutionRequestPayload(StrictModel):
    """Represents execution request payload."""

    artifact_id: str | None = None
    request_text: str | None = None
    vector: tuple[float, ...] | None = None
    top_k: int = Field(gt=0, default=5)
    execution_contract: ExecutionContract
    execution_intent: ExecutionIntent
    execution_mode: ExecutionMode = ExecutionMode.STRICT
    execution_budget: ExecutionBudgetPayload | None = None
    randomness_profile: RandomnessProfilePayload | None = None
    nd_profile: str | None = None
    nd_target_recall: float | None = None
    nd_latency_budget_ms: int | None = None
    nd_witness_rate: float | None = None
    nd_witness_sample_k: int | None = None
    nd_witness_mode: str | None = None
    nd_build_on_demand: bool = False
    nd_candidate_k: int | None = None
    nd_diversity_lambda: float | None = None
    nd_normalize_vectors: bool = False
    nd_normalize_query: bool = False
    nd_outlier_threshold: float | None = None
    nd_low_signal_margin: float | None = None
    nd_adaptive_k: bool = False
    nd_low_signal_refuse: bool = False
    nd_replay_strict: bool = False
    nd_warmup_queries: str | None = None
    nd_incremental_index: bool | None = None
    nd_max_candidates: int | None = None
    nd_max_index_memory_mb: int | None = None
    nd_two_stage: bool = True
    nd_m: int | None = None
    nd_ef_construction: int | None = None
    nd_ef_search: int | None = None
    nd_max_ef_search: int | None = None
    nd_space: str | None = None
    correlation_id: str | None = None
    vector_store: str | None = None
    vector_store_uri: str | None = None
    vector_store_options: dict[str, str] | None = None

    @model_validator(mode="after")  # type: ignore[untyped-decorator]
    def ensure_one_of_request_or_vector(self) -> Self:
        """Ensure one of request or vector."""
        if self.request_text is None and self.vector is None:
            raise ValueError("request_text or vector is required")
        return self

    @model_validator(mode="after")  # type: ignore[untyped-decorator]
    def ensure_randomness_for_nd(self) -> Self:
        """Ensure randomness for ND."""
        from bijux_canon_index.interfaces.schemas.validators import (
            validate_execution_request_payload,
        )

        validate_execution_request_payload(self)
        return self


class ExecutionArtifactRequest(StrictModel):
    """Represents execution artifact request."""

    execution_contract: ExecutionContract
    index_mode: str | None = None
    vector_store: str | None = None
    vector_store_uri: str | None = None
    vector_store_options: dict[str, str] | None = None

    @model_validator(mode="after")  # type: ignore[untyped-decorator]
    def ensure_index_mode(self) -> Self:
        """Ensure index mode."""
        if self.index_mode is None:
            return self
        if self.index_mode not in {"exact", "ann"}:
            raise ValueError("index_mode must be exact|ann")
        return self


class ExplainRequest(StrictModel):
    """Represents explain request."""

    result_id: str = Field(min_length=1)
    artifact_id: str | None = None


__all__ = [
    "CreateRequest",
    "ExecutionArtifactRequest",
    "ExecutionBudgetPayload",
    "ExecutionRequestPayload",
    "ExplainRequest",
    "IngestRequest",
    "RandomnessProfilePayload",
]
