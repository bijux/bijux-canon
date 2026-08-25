# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Strict transport schemas for the Runtime v2 HTTP API."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from bijux_canon_runtime.application.problems import RuntimeProblemCode
from bijux_canon_runtime.model.execution.request_plan import (
    MAX_RUNTIME_TIMEOUT_SECONDS,
)

ArtifactIdentity = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
ContentDigest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
StableIdentity = Annotated[str, Field(min_length=1, max_length=200)]
Cursor = Annotated[str, Field(min_length=1, max_length=4096)]
ReadinessReasonValue = Literal[
    "workspace-not-configured",
    "workspace-invalid",
    "database-not-configured",
    "schema-unavailable",
    "artifact-store-not-configured",
    "artifact-store-unavailable",
    "index-not-configured",
    "active-generation-unavailable",
    "model-configuration-unavailable",
    "provider-configuration-unavailable",
    "state-not-writable",
]


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

    timeout_seconds: Annotated[
        float, Field(gt=0, le=MAX_RUNTIME_TIMEOUT_SECONDS)
    ]
    max_artifact_bytes: Annotated[int, Field(ge=1)]
    max_steps: Annotated[int | None, Field(ge=1)] = None
    max_provider_tokens: Annotated[int | None, Field(ge=1)] = None


class Filters(StrictModel):
    """Immutable retrieval filters."""

    document_ids: Annotated[tuple[str, ...], Field(max_length=1000)] = ()
    source_uris: Annotated[tuple[str, ...], Field(max_length=1000)] = ()


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


class RetrievalEvaluationRequest(StrictModel):
    """Evaluate reviewed local questions through one immutable index artifact."""

    cases_path: Annotated[str, Field(min_length=1)]
    qrels_path: Annotated[str, Field(min_length=1)]
    index_id: ArtifactIdentity
    split: Annotated[str, Field(min_length=1)] = "development"
    mode: Literal[
        "offline-lexical",
        "local-hybrid-exact",
        "local-hybrid-ann",
    ] = "local-hybrid-ann"
    top_k: Annotated[int, Field(ge=10, le=1000)] = 10


class AnswerEvaluationRequest(StrictModel):
    """Adapt one persisted grounded answer without supplying truth labels."""

    case_id: StableIdentity
    question: Annotated[str, Field(min_length=1, max_length=32768)]
    run_id: StableIdentity
    attempt_id: StableIdentity | None = None


class RetrievalLocatorSegmentResponse(StrictModel):
    """One exact content-bound citation locator segment."""

    ordinal: Annotated[int, Field(ge=0)]
    mapping_id: ArtifactIdentity
    scheme: Annotated[str, Field(min_length=1)]
    selectors: tuple[tuple[str, str | int], ...]
    content_sha256: ContentDigest


class RetrievalObservedHitResponse(StrictModel):
    """One installed ranked hit with exact document and locator lineage."""

    rank: Annotated[int, Field(ge=1)]
    retrieval_rank: Annotated[int, Field(ge=1)]
    score: float
    chunk_id: Annotated[str, Field(min_length=1)]
    document_id: Annotated[str, Field(min_length=1)]
    source_content_sha256: ContentDigest
    content_sha256: ContentDigest
    locator_segments: Annotated[
        tuple[RetrievalLocatorSegmentResponse, ...], Field(min_length=1)
    ]


class RetrievalStageCandidateResponse(StrictModel):
    """One raw channel candidate retained for development diagnosis."""

    stage: Literal["lexical", "dense", "fusion", "rerank"]
    chunk_id: Annotated[str, Field(min_length=1)]
    source_rank: Annotated[int, Field(ge=1)]
    output_rank: Annotated[int | None, Field(ge=1)]
    score: float
    disposition: Annotated[str, Field(min_length=1)]


class RetrievalStageEvidenceResponse(StrictModel):
    """Raw stage rankings used to prove candidate conservation."""

    lexical_outcome: Annotated[str, Field(min_length=1)]
    dense_outcome: str | None
    fusion_policy_sha256: ContentDigest | None
    rerank_policy_sha256: ContentDigest | None
    lexical_candidates: tuple[RetrievalStageCandidateResponse, ...]
    dense_candidates: tuple[RetrievalStageCandidateResponse, ...]
    fusion_candidates: tuple[RetrievalStageCandidateResponse, ...]
    rerank_candidates: tuple[RetrievalStageCandidateResponse, ...]


class RetrievalExecutionObservationResponse(StrictModel):
    """One persisted installed query execution, including non-usable outcomes."""

    query_id: Annotated[str, Field(min_length=1)]
    query_text_sha256: ContentDigest
    status: Literal["success", "insufficient", "refused", "failed"]
    generation_id: ArtifactIdentity
    model_lock_artifact_id: ArtifactIdentity
    configuration_id: ArtifactIdentity
    retrieval_mode: Literal[
        "lexical", "offline-lexical", "local-hybrid-exact", "local-hybrid-ann"
    ]
    hits: tuple[RetrievalObservedHitResponse, ...]
    run_id: str | None
    attempt_id: str | None
    vex_artifact_id: ArtifactIdentity | None
    policy_action: Annotated[str, Field(min_length=1)]
    fallback_action: Annotated[str, Field(min_length=1)]
    stages: RetrievalStageEvidenceResponse | None
    failure: str | None


class RetrievalGradedQrelResponse(StrictModel):
    """One independently reviewed relevance grade used in metric arithmetic."""

    evidence_id: Annotated[str, Field(min_length=1)]
    relevance_grade: Annotated[int, Field(ge=0, le=3)]


class RetrievalRankedHitResponse(StrictModel):
    """One scored hit in deterministic metric order."""

    evidence_id: Annotated[str, Field(min_length=1)]
    score: float


class RetrievalQueryMetricsResponse(StrictModel):
    """Exact per-question ranking arithmetic."""

    query_id: Annotated[str, Field(min_length=1)]
    input_identity_sha256: ContentDigest
    graded_qrels: tuple[RetrievalGradedQrelResponse, ...]
    ordered_hits: tuple[RetrievalRankedHitResponse, ...]
    ordered_evidence_ids: tuple[str, ...]
    relevant_evidence_ids: tuple[str, ...]
    retrieved_relevant_at_5: tuple[str, ...]
    recall_at_5_numerator: Annotated[int, Field(ge=0)]
    recall_at_5_denominator: Annotated[int, Field(ge=1)]
    recall_at_5: Annotated[float, Field(ge=0, le=1)]
    first_relevant_rank_at_10: Annotated[int | None, Field(ge=1, le=10)]
    reciprocal_rank_at_10: Annotated[float, Field(ge=0, le=1)]
    graded_gains_at_10: tuple[int, ...]
    ideal_graded_gains_at_10: tuple[int, ...]
    dcg_at_10: Annotated[float, Field(ge=0)]
    ideal_dcg_at_10: Annotated[float, Field(ge=0)]
    ndcg_at_10: Annotated[float, Field(ge=0, le=1)]
    evidence_sha256: ContentDigest


class RetrievalMetricIntervalResponse(StrictModel):
    """Declared confidence interval for one macro retrieval metric."""

    level: Annotated[float, Field(gt=0, lt=1)]
    lower: Annotated[float, Field(ge=0, le=1)]
    upper: Annotated[float, Field(ge=0, le=1)]
    method: Annotated[str, Field(min_length=1)]


class RetrievalAggregateMetricResponse(StrictModel):
    """Macro metric with its complete numerator, samples, and denominator."""

    metric_id: Annotated[str, Field(min_length=1)]
    value: Annotated[float, Field(ge=0, le=1)]
    numerator: Annotated[float, Field(ge=0)]
    denominator: Annotated[int, Field(ge=1)]
    formula: Annotated[str, Field(min_length=1)]
    samples: tuple[float, ...]
    confidence_interval: RetrievalMetricIntervalResponse


class RetrievalMacroReportResponse(StrictModel):
    """All per-query and macro retrieval metrics."""

    schema_version: Literal["bijux.canon.index.retrieval-evaluation.v1"]
    queries: Annotated[tuple[RetrievalQueryMetricsResponse, ...], Field(min_length=1)]
    metrics: Annotated[
        tuple[RetrievalAggregateMetricResponse, ...], Field(min_length=3, max_length=3)
    ]
    evidence_sha256: ContentDigest


class RetrievalPooledCountsResponse(StrictModel):
    """Transparent micro-population counts across reviewed judgments."""

    relevant_qrels: Annotated[int, Field(ge=1)]
    retrieved_relevant_at_5: Annotated[int, Field(ge=0)]
    recall_at_5: Annotated[float, Field(ge=0, le=1)]
    total_ranked_hits: Annotated[int, Field(ge=0)]
    refused_queries: Annotated[int, Field(ge=0)]
    failed_queries: Annotated[int, Field(ge=0)]


class RelevantEvidenceStageTraceResponse(StrictModel):
    """Ranks and first accountable loss point for one reviewed qrel."""

    qrel_id: Annotated[str, Field(min_length=1)]
    chunk_id: Annotated[str, Field(min_length=1)]
    relevance_grade: Annotated[int, Field(ge=0, le=3)]
    lexical_source_rank: Annotated[int | None, Field(ge=1)]
    lexical_output_rank: Annotated[int | None, Field(ge=1)]
    lexical_disposition: str | None
    dense_rank: Annotated[int | None, Field(ge=1)]
    fusion_rank: Annotated[int | None, Field(ge=1)]
    rerank_rank: Annotated[int | None, Field(ge=1)]
    final_rank: Annotated[int | None, Field(ge=1)]
    disposition: Literal[
        "retained_at_5",
        "final_below_5",
        "absent_from_candidate_depth",
        "excluded_by_channel_limit",
        "lost_at_fusion_limit",
        "lost_at_rerank_limit",
        "lost_at_finalization",
        "execution_refused",
        "execution_failed",
    ]


class QueryStageDiagnosticsResponse(StrictModel):
    """Per-question stage population and qrel losses."""

    query_id: Annotated[str, Field(min_length=1)]
    lexical_observed_count: Annotated[int, Field(ge=0)]
    lexical_included_count: Annotated[int, Field(ge=0)]
    dense_observed_count: Annotated[int, Field(ge=0)]
    fusion_count: Annotated[int, Field(ge=0)]
    rerank_count: Annotated[int, Field(ge=0)]
    final_count: Annotated[int, Field(ge=0)]
    relevant_evidence: Annotated[
        tuple[RelevantEvidenceStageTraceResponse, ...], Field(min_length=1)
    ]


class RetrievalStageRecallResponse(StrictModel):
    """Exact qrel numerator and denominator at one retrieval stage."""

    stage_id: Literal[
        "candidate-depth",
        "channel-admitted",
        "fusion-at-10",
        "rerank-at-10",
        "final-at-10",
        "final-at-5",
    ]
    numerator: Annotated[int, Field(ge=0)]
    denominator: Annotated[int, Field(ge=1)]
    value: Annotated[float, Field(ge=0, le=1)]


class RetrievalStageAnalysisResponse(StrictModel):
    """Compact loss counts plus every per-query qrel trace."""

    schema_version: Literal["bijux.canon.index.retrieval-stage-analysis.v2"]
    query_count: Annotated[int, Field(ge=1)]
    qrel_count: Annotated[int, Field(ge=1)]
    recall: tuple[RetrievalStageRecallResponse, ...]
    disposition_counts: tuple[tuple[str, Annotated[int, Field(ge=0)]], ...]
    queries: Annotated[tuple[QueryStageDiagnosticsResponse, ...], Field(min_length=1)]


class RetrievalEvaluationResponse(StrictModel):
    """Transparent metrics and exact observations from installed retrieval."""

    schema_version: Literal["bijux.canon.index.public-retrieval-evaluation.v2"]
    request_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    query_count: Annotated[int, Field(ge=1)]
    qrel_count: Annotated[int, Field(ge=1)]
    generation_ids: Annotated[tuple[ArtifactIdentity, ...], Field(min_length=1)]
    model_lock_artifact_ids: Annotated[
        tuple[ArtifactIdentity, ...], Field(min_length=1)
    ]
    configuration_ids: Annotated[tuple[ArtifactIdentity, ...], Field(min_length=1)]
    observations: Annotated[
        tuple[RetrievalExecutionObservationResponse, ...], Field(min_length=1)
    ]
    macro: RetrievalMacroReportResponse
    micro: RetrievalPooledCountsResponse
    stage_analysis: RetrievalStageAnalysisResponse
    worst_query_ids: tuple[str, ...]
    evidence_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


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
    timeout_seconds: Annotated[
        float | None, Field(gt=0, le=MAX_RUNTIME_TIMEOUT_SECONDS)
    ] = None


class CompareRequest(StrictModel):
    """Compare two explicit immutable attempts."""

    context: RequestContext
    baseline_run_id: StableIdentity
    baseline_attempt_id: StableIdentity
    candidate_run_id: StableIdentity
    candidate_attempt_id: StableIdentity
    dimensions: Annotated[
        tuple[
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
        ],
        Field(min_length=1, max_length=12),
    ]
    cursor: Cursor | None = None
    limit: Annotated[int, Field(ge=1, le=1000)] = 100


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


class CursorPageResponse(StrictModel):
    """Stable page metadata bound to one immutable response snapshot."""

    limit: Annotated[int, Field(ge=1, le=1000)]
    next_cursor: str | None
    next_offset: Annotated[int | None, Field(ge=0)]
    offset: Annotated[int, Field(ge=0)]
    snapshot_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class LivenessResponse(StrictModel):
    """Dependency-free process liveness."""

    schema_version: Literal["bijux.runtime.liveness.v1"]
    live: Literal[True]
    status: Literal["ok"]


class ReadinessCheckResponse(StrictModel):
    """One safe typed dependency verdict."""

    name: Literal[
        "workspace-initialization",
        "schema-migrations",
        "artifact-store",
        "active-generation",
        "model-configuration",
        "provider-configuration",
        "writable-state",
    ]
    ready: bool
    reason: ReadinessReasonValue | None
    remediation: str | None


class ReadinessResponse(StrictModel):
    """Conjunctive deep readiness with typed degraded reasons."""

    schema_version: Literal["bijux.runtime.readiness.v2"]
    capability: Literal[
        "initialized", "ingest", "index", "retrieve", "ask", "research", "run"
    ]
    ready: bool
    status: Literal["ready", "degraded"]
    checks: tuple[ReadinessCheckResponse, ...]
    reasons: tuple[ReadinessReasonValue, ...]


class InstalledDistributionDiscoveryResponse(StrictModel):
    """Exact installed version of one canonical package."""

    name: str
    version: str


class ParserDiscoveryResponse(StrictModel):
    """One source format and its installed admission disposition."""

    format_id: Literal[
        "jats",
        "pdf-digital",
        "html",
        "markdown",
        "text",
        "docx",
        "ocr-required",
    ]
    disposition: Literal["supported", "typed_refusal"]


class ProviderDiscoveryResponse(StrictModel):
    """One provider identifier accepted by installed reasoning."""

    provider_id: Literal["credential-free", "local-recorded"]
    provider_kind: Literal["local"]
    credential_required: Literal[False]


class WorkspaceDiscoveryResponse(StrictModel):
    """Content-safe effective workspace identity."""

    status: Literal["not_configured", "unavailable", "initialized"]
    workspace_id: str | None
    workspace_version: int | None
    layout_identity_sha256: str | None


class ModelDiscoveryResponse(StrictModel):
    """Content-safe effective embedding-model identity."""

    status: Literal["not_configured", "unavailable", "verified"]
    model_lock_artifact_id: str | None
    profile_id: str | None
    provider_kind: str | None
    model_id: str | None
    revision: str | None
    dimension: int | None
    validation_record_id: str | None
    artifact_set_digest: str | None
    license_pointer: str | None
    compatibility_status: str | None
    validation_result: str | None
    offline_reuse: bool


class IndexDiscoveryResponse(StrictModel):
    """Content-safe active index identity."""

    status: Literal["not_configured", "unavailable", "active"]
    generation_id: str | None
    snapshot_artifact_id: str | None
    model_lock_artifact_id: str | None
    chunk_set_sha256: str | None
    chunk_count: int | None
    dimension: int | None


class RuntimeCapabilityDiscoveryResponse(StrictModel):
    """Secret-safe effective product configuration and support discovery."""

    schema_version: Literal["bijux.runtime.capability-discovery.v1"]
    configuration: dict[str, object]
    provider_credential_available: bool
    workspace: WorkspaceDiscoveryResponse
    model: ModelDiscoveryResponse
    index: IndexDiscoveryResponse
    installed_distributions: tuple[InstalledDistributionDiscoveryResponse, ...]
    operations: tuple[str, ...]
    parsers: tuple[ParserDiscoveryResponse, ...]
    providers: tuple[ProviderDiscoveryResponse, ...]
    readiness: tuple[ReadinessResponse, ...]


class CorpusParserIdentityResponse(StrictModel):
    """Installed parser contract represented in an immutable corpus."""

    name: Annotated[str, Field(min_length=1, max_length=200)]
    version: Annotated[str, Field(min_length=1, max_length=100)]
    schema_version: Annotated[str, Field(min_length=1, max_length=200)]


class CorpusInspectionResponse(StrictModel):
    """Verified immutable corpus publication metadata."""

    schema_version: Literal["bijux.canon.ingest.corpus_publication.v1"]
    snapshot_id: ArtifactIdentity
    canonical_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    byte_length: Annotated[int, Field(ge=1)]
    document_count: Annotated[int, Field(ge=0)]
    chunk_count: Annotated[int, Field(ge=0)]
    rejection_count: Annotated[int, Field(ge=0)]
    parser_identities: Annotated[
        tuple[CorpusParserIdentityResponse, ...], Field(max_length=100)
    ]
    generation_name: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class IndexInspectionResponse(StrictModel):
    """Content-safe immutable index generation metadata."""

    schema_version: Literal["bijux.canon.index.inspection.v1"]
    generation_id: ArtifactIdentity
    snapshot_artifact_id: StableIdentity
    model_lock_artifact_id: StableIdentity
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
    page: CursorPageResponse


class ProblemDetail(StrictModel):
    """Safe RFC 9457-style failure shared by every v2 route."""

    schema_version: Literal["bijux.runtime.problem.v2"]
    type: str
    title: str
    status: int
    code: RuntimeProblemCode
    correlation_id: str
    run_id: str | None
    retryable: bool
    remediation: str
    cause: str | None


__all__ = [
    "AnswerEvaluationRequest",
    "AskRequest",
    "BuildIndexRequest",
    "CancelRequest",
    "CompareRequest",
    "CorpusInspectionResponse",
    "CursorPageResponse",
    "IndexInspectionResponse",
    "JobResultResponse",
    "JobStatusResponse",
    "LivenessResponse",
    "PrepareCorpusRequest",
    "ProblemDetail",
    "ReadinessCheckResponse",
    "ReadinessResponse",
    "ReplayRequest",
    "ResearchRequest",
    "RetrievalEvaluationRequest",
    "RetrievalEvaluationResponse",
    "RetrieveRequest",
    "RunRequest",
    "RuntimeCapabilityDiscoveryResponse",
]
