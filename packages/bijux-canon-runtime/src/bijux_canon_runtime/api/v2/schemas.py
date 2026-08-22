# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Strict transport schemas for the Runtime v2 HTTP API."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

ArtifactIdentity = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
StableIdentity = Annotated[str, Field(min_length=1, max_length=200)]


class StrictModel(BaseModel):
    """Reject unknown transport fields instead of silently dropping intent."""

    model_config = ConfigDict(extra="forbid")


class RequestContext(StrictModel):
    """Versioned caller and correlation identity."""

    contract_version: Literal["v2"]
    request_id: StableIdentity
    correlation_id: StableIdentity
    replay_mode: Literal["strict", "bounded", "observational"] = "strict"


class Budget(StrictModel):
    """Hard execution and persistence bounds."""

    timeout_seconds: Annotated[float, Field(gt=0)]
    max_artifact_bytes: Annotated[int, Field(ge=1)]
    max_steps: Annotated[int | None, Field(ge=1)] = None
    max_provider_tokens: Annotated[int | None, Field(ge=1)] = None


class Filters(StrictModel):
    """Immutable retrieval filters."""

    document_ids: tuple[str, ...] = ()
    source_uris: tuple[str, ...] = ()


class AnswerPolicy(StrictModel):
    """Grounding and publication requirements."""

    provider: Annotated[str, Field(min_length=1)]
    require_citations: bool = True
    permit_insufficient_answer: bool = True
    publish: bool = True


class PrepareCorpusRequest(StrictModel):
    """Prepare a corpus from one explicit local directory."""

    context: RequestContext
    source_directory: Annotated[str, Field(min_length=1)]
    scope: Annotated[str, Field(min_length=1)]
    budget: Budget
    execution_profile: Literal[
        "offline-lexical",
        "local-hybrid-exact",
        "local-hybrid-ann",
        "qdrant-hybrid",
    ] = "local-hybrid-exact"


class BuildIndexRequest(StrictModel):
    """Build immutable indexes for one corpus artifact."""

    context: RequestContext
    corpus_id: ArtifactIdentity
    scope: Annotated[str, Field(min_length=1)]
    budget: Budget
    execution_profile: Literal[
        "offline-lexical",
        "local-hybrid-exact",
        "local-hybrid-ann",
        "qdrant-hybrid",
    ]


class RetrieveRequest(StrictModel):
    """Retrieve bounded evidence from one index artifact."""

    context: RequestContext
    query: Annotated[str, Field(min_length=1, max_length=32768)]
    index_id: ArtifactIdentity
    scope: Annotated[str, Field(min_length=1)]
    top_k: Annotated[int, Field(ge=1, le=1000)]
    filters: Filters = Filters()
    budget: Budget
    execution_profile: Literal[
        "offline-lexical",
        "local-hybrid-exact",
        "local-hybrid-ann",
        "qdrant-hybrid",
    ]


class AskRequest(RetrieveRequest):
    """Produce a grounded answer from retrieved evidence."""

    corpus_id: ArtifactIdentity
    answer_policy: AnswerPolicy


class ResearchRequest(AskRequest):
    """Run bounded research with counterevidence authority."""


class RunRequest(StrictModel):
    """Submit a complete linked Runtime workflow."""

    context: RequestContext
    query: Annotated[str, Field(min_length=1, max_length=32768)]
    scope: Annotated[str, Field(min_length=1)]
    corpus_id: ArtifactIdentity | None = None
    source_directory: str | None = None
    top_k: Annotated[int, Field(ge=1, le=1000)]
    filters: Filters = Filters()
    answer_policy: AnswerPolicy
    budget: Budget
    execution_profile: Literal[
        "offline-lexical",
        "local-hybrid-exact",
        "local-hybrid-ann",
        "qdrant-hybrid",
    ]


class ReplayRequest(StrictModel):
    """Create a replay from one immutable source attempt."""

    context: RequestContext
    source_attempt_id: StableIdentity
    process_id: StableIdentity
    network_policy: Literal["disabled", "recorded-only", "permitted"]
    provider_allowlist: tuple[str, ...] = ()
    timeout_seconds: Annotated[float | None, Field(gt=0)] = None


class CompareRequest(StrictModel):
    """Compare two explicit immutable attempts."""

    context: RequestContext
    baseline_run_id: StableIdentity
    baseline_attempt_id: StableIdentity
    candidate_run_id: StableIdentity
    candidate_attempt_id: StableIdentity
    dimensions: tuple[
        Literal[
            "dag",
            "configuration",
            "corpus",
            "index",
            "model",
            "retrieval",
            "claims",
            "citations",
            "provider-calls",
            "timing",
            "policy",
            "outcome",
        ],
        ...,
    ]


class CancelRequest(StrictModel):
    """Auditable caller reason for cooperative cancellation."""

    context: RequestContext
    reason: Annotated[str, Field(min_length=1, max_length=1000)]


class JobStatusResponse(StrictModel):
    """Restart-safe durable job state."""

    schema_version: Literal["bijux.runtime.http-job-status.v2"]
    job_id: str
    kind: Literal["run", "replay"]
    status: Literal[
        "queued", "running", "succeeded", "failed", "cancelled", "timed_out"
    ]
    cancel_requested: bool
    attempt_count: int
    submitted_at: str
    started_at: str | None
    finished_at: str | None
    deadline_at: str | None
    timeout_seconds: float | None
    result_available: bool
    error_type: str | None
    error_message: str | None
    status_uri: str
    result_uri: str
    cancellation_uri: str


class JobResultResponse(StrictModel):
    """Typed successful result returned by the application executor."""

    schema_version: Literal["bijux.runtime.http-job-result.v2"]
    job_id: str
    result: dict[str, object]


class CorpusInspectionResponse(StrictModel):
    """Verified immutable corpus publication metadata."""

    schema_version: Literal["bijux.canon.ingest.corpus_publication.v1"]
    snapshot_id: ArtifactIdentity
    canonical_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    byte_length: Annotated[int, Field(ge=1)]
    generation_name: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class IndexInspectionResponse(StrictModel):
    """Content-safe immutable index generation metadata."""

    schema_version: Literal["bijux.canon.index.inspection.v1"]
    generation_id: ArtifactIdentity
    snapshot_artifact_id: ArtifactIdentity
    model_lock_artifact_id: ArtifactIdentity
    chunk_set_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    chunk_count: Annotated[int, Field(ge=1)]
    dimension: Annotated[int, Field(ge=1)]
    text_bytes: Annotated[int, Field(ge=0)]
    vector_bytes: Annotated[int, Field(ge=0)]
    metadata_bytes: Annotated[int, Field(ge=0)]
    segments: tuple[dict[str, object], ...]
    filters: dict[str, object]
    lineage: dict[str, object]
    integrity: dict[str, object]
    activation: dict[str, object]
    compatibility: dict[str, object]


class ProblemDetail(StrictModel):
    """Safe RFC 9457-style failure shared by every v2 route."""

    type: str
    title: str
    status: int
    code: str
    correlation_id: str
    retryable: bool
    remediation: str
    cause: str | None = None


__all__ = [
    "AskRequest",
    "BuildIndexRequest",
    "CancelRequest",
    "CompareRequest",
    "CorpusInspectionResponse",
    "IndexInspectionResponse",
    "JobResultResponse",
    "JobStatusResponse",
    "PrepareCorpusRequest",
    "ProblemDetail",
    "ReplayRequest",
    "ResearchRequest",
    "RetrieveRequest",
    "RunRequest",
]
