# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Public-path retrieval evaluation over reviewed questions and observed hits."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum
import hashlib
import json
import math
from pathlib import Path

from bijux_canon_index.evaluation.retrieval_metrics import (
    GradedQrel,
    RankedRetrievalHit,
    RetrievalEvaluationCase,
    RetrievalEvaluationReport,
    RetrievalMetricEvaluator,
)
from bijux_canon_index.evaluation.stage_diagnostics import (
    RetrievalStageAnalysis,
    RetrievalStageEvidence,
    aggregate_stage_analysis,
    analyze_query_stages,
)


class PublicRetrievalEvaluationError(ValueError):
    """Reviewed truth or observed public-path evidence is incomplete or unsafe."""


class PublicRetrievalMode(StrEnum):
    """Installed retrieval modes admitted by the evaluator."""

    lexical = "offline-lexical"
    hybrid_exact = "local-hybrid-exact"
    hybrid_ann = "local-hybrid-ann"


class RetrievalExecutionStatus(StrEnum):
    """Whether one installed query produced usable ranked evidence."""

    success = "success"
    insufficient = "insufficient"
    refused = "refused"
    failed = "failed"


@dataclass(frozen=True, slots=True)
class ReviewedRetrievalQrel:
    """One question-specific reviewed judgment resolved to an immutable chunk."""

    qrel_id: str
    chunk_id: str
    relevance_grade: int
    relation: str
    qrel_identity_sha256: str

    def __post_init__(self) -> None:
        if not all(
            value.strip() for value in (self.qrel_id, self.chunk_id, self.relation)
        ):
            raise ValueError("reviewed retrieval qrel fields must not be empty")
        if not _is_sha256(self.qrel_identity_sha256):
            raise ValueError("reviewed retrieval qrel identity must be a SHA-256")
        if isinstance(self.relevance_grade, bool) or not 0 <= self.relevance_grade <= 3:
            raise ValueError("reviewed retrieval relevance grade must be within 0..3")


@dataclass(frozen=True, slots=True)
class ReviewedRetrievalQuery:
    """One independently reviewed query; ranked hits are intentionally absent."""

    query_id: str
    query_text: str
    input_identity_sha256: str
    qrels: tuple[ReviewedRetrievalQrel, ...]

    def __post_init__(self) -> None:
        if not self.query_id.strip() or not self.query_text.strip():
            raise ValueError("reviewed retrieval query identity and text are required")
        if not _is_sha256(self.input_identity_sha256):
            raise ValueError(
                "reviewed retrieval query input identity must be a SHA-256"
            )
        if not self.qrels:
            raise ValueError("reviewed retrieval query must contain qrels")
        qrel_ids = tuple(item.qrel_id for item in self.qrels)
        chunk_ids = tuple(item.chunk_id for item in self.qrels)
        if len(qrel_ids) != len(set(qrel_ids)):
            raise ValueError(
                "reviewed retrieval qrel identities must be unique per query"
            )
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("reviewed retrieval chunks must be unique per query")
        if not any(item.relevance_grade > 0 for item in self.qrels):
            raise ValueError("reviewed retrieval query needs positive evidence")


@dataclass(frozen=True, slots=True)
class PublicRetrievalEvaluationRequest:
    """Truth-only request executed by an installed retriever, never supplied hits."""

    schema_version: str
    index_artifact_id: str
    split: str
    mode: PublicRetrievalMode
    top_k: int
    candidate_limit: int
    queries: tuple[ReviewedRetrievalQuery, ...]
    request_sha256: str

    def __post_init__(self) -> None:
        if self.schema_version != "bijux.canon.index.public-retrieval-request.v1":
            raise ValueError(
                "public retrieval evaluation request schema is unsupported"
            )
        if not _is_artifact_id(self.index_artifact_id):
            raise ValueError(
                "public retrieval evaluation requires an index artifact ID"
            )
        if not self.split.strip():
            raise ValueError("public retrieval evaluation split must not be empty")
        if not 10 <= self.top_k <= 1000:
            raise ValueError(
                "public retrieval evaluation top_k must be within 10..1000"
            )
        if not self.top_k <= self.candidate_limit <= 1000:
            raise ValueError("public retrieval candidate limit must include top_k")
        query_ids = tuple(query.query_id for query in self.queries)
        if not query_ids or len(query_ids) != len(set(query_ids)):
            raise ValueError("public retrieval evaluation queries must be unique")
        expected = _sha256(
            {
                "candidate_limit": self.candidate_limit,
                "index_artifact_id": self.index_artifact_id,
                "mode": self.mode.value,
                "queries": [asdict(query) for query in self.queries],
                "schema_version": self.schema_version,
                "split": self.split,
                "top_k": self.top_k,
            }
        )
        if self.request_sha256 != expected:
            raise ValueError("public retrieval evaluation request identity mismatch")

    @classmethod
    def create(
        cls,
        *,
        index_artifact_id: str,
        split: str,
        mode: PublicRetrievalMode,
        queries: tuple[ReviewedRetrievalQuery, ...],
        top_k: int = 10,
    ) -> PublicRetrievalEvaluationRequest:
        """Create a content-addressed truth-only public evaluation request."""

        schema_version = "bijux.canon.index.public-retrieval-request.v1"
        candidate_limit = min(1000, top_k * 4)
        payload = {
            "candidate_limit": candidate_limit,
            "index_artifact_id": index_artifact_id,
            "mode": mode.value,
            "queries": [asdict(query) for query in queries],
            "schema_version": schema_version,
            "split": split,
            "top_k": top_k,
        }
        return cls(
            schema_version=schema_version,
            index_artifact_id=index_artifact_id,
            split=split,
            mode=mode,
            top_k=top_k,
            candidate_limit=candidate_limit,
            queries=queries,
            request_sha256=_sha256(payload),
        )


@dataclass(frozen=True, slots=True)
class ObservedLocatorSegment:
    """Content-bound exact locator retained without copying source text."""

    ordinal: int
    mapping_id: str
    scheme: str
    selectors: tuple[tuple[str, str | int], ...]
    content_sha256: str


@dataclass(frozen=True, slots=True)
class ObservedRetrievalHit:
    """One raw installed retrieval hit and its exact citation lineage."""

    rank: int
    retrieval_rank: int
    score: float
    chunk_id: str
    document_id: str
    source_content_sha256: str
    content_sha256: str
    locator_segments: tuple[ObservedLocatorSegment, ...]

    def __post_init__(self) -> None:
        if self.rank < 1 or self.retrieval_rank < 1:
            raise ValueError("observed retrieval ranks must be positive")
        if not math.isfinite(self.score):
            raise ValueError("observed retrieval score must be finite")
        if not self.chunk_id.strip() or not self.document_id.strip():
            raise ValueError("observed retrieval identities must not be empty")
        if not _is_sha256(self.source_content_sha256) or not _is_sha256(
            self.content_sha256
        ):
            raise ValueError("observed retrieval content identities are invalid")
        if not self.locator_segments:
            raise ValueError("observed retrieval hits require exact locator segments")


@dataclass(frozen=True, slots=True)
class RetrievalExecutionObservation:
    """Complete evidence from one installed retrieval execution."""

    query_id: str
    query_text_sha256: str
    status: RetrievalExecutionStatus
    generation_id: str
    model_lock_artifact_id: str
    configuration_id: str
    retrieval_mode: str
    hits: tuple[ObservedRetrievalHit, ...]
    run_id: str | None
    attempt_id: str | None
    vex_artifact_id: str | None
    policy_action: str
    fallback_action: str
    stages: RetrievalStageEvidence | None
    failure: str | None

    def __post_init__(self) -> None:
        if not self.query_id.strip() or not _is_sha256(self.query_text_sha256):
            raise ValueError("retrieval observation query identity is invalid")
        if not all(
            value.strip()
            for value in (
                self.generation_id,
                self.model_lock_artifact_id,
                self.configuration_id,
                self.retrieval_mode,
                self.policy_action,
                self.fallback_action,
            )
        ):
            raise ValueError("retrieval observation provenance is incomplete")
        ranks = tuple(hit.rank for hit in self.hits)
        chunk_ids = tuple(hit.chunk_id for hit in self.hits)
        if ranks != tuple(range(1, len(ranks) + 1)):
            raise ValueError("observed retrieval hit ranks must be contiguous")
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("observed retrieval hit identities must be unique")
        if self.status in {
            RetrievalExecutionStatus.refused,
            RetrievalExecutionStatus.failed,
        }:
            if self.hits or self.stages is not None or not self.failure:
                raise ValueError(
                    "refused or failed retrieval must retain only its failure"
                )
        else:
            if self.failure is not None:
                raise ValueError(
                    "successful retrieval observations cannot retain a failure"
                )
            if self.stages is None:
                raise ValueError(
                    "successful retrieval observations require raw stage evidence"
                )


@dataclass(frozen=True, slots=True)
class PooledRetrievalCounts:
    """Micro-population arithmetic across all unique query judgments."""

    relevant_qrels: int
    retrieved_relevant_at_5: int
    recall_at_5: float
    total_ranked_hits: int
    refused_queries: int
    failed_queries: int


@dataclass(frozen=True, slots=True)
class PublicRetrievalEvaluationReport:
    """Integrity-bound public-path observations and transparent aggregates."""

    schema_version: str
    request_sha256: str
    query_count: int
    qrel_count: int
    generation_ids: tuple[str, ...]
    model_lock_artifact_ids: tuple[str, ...]
    configuration_ids: tuple[str, ...]
    observations: tuple[RetrievalExecutionObservation, ...]
    macro: RetrievalEvaluationReport
    micro: PooledRetrievalCounts
    stage_analysis: RetrievalStageAnalysis
    worst_query_ids: tuple[str, ...]
    evidence_sha256: str

    def __post_init__(self) -> None:
        if self.schema_version != "bijux.canon.index.public-retrieval-evaluation.v2":
            raise ValueError("public retrieval evaluation report schema is unsupported")
        if self.query_count != len(self.observations) or self.query_count < 1:
            raise ValueError("public retrieval query denominator is invalid")
        if len(self.macro.queries) != self.query_count:
            raise ValueError("public and macro query denominators diverge")
        if (
            self.stage_analysis.query_count != self.query_count
            or self.stage_analysis.qrel_count != self.qrel_count
        ):
            raise ValueError("public and stage-analysis denominators diverge")
        final_at_5 = next(
            item for item in self.stage_analysis.recall if item.stage_id == "final-at-5"
        )
        if (
            final_at_5.numerator != self.micro.retrieved_relevant_at_5
            or final_at_5.denominator != self.micro.relevant_qrels
        ):
            raise ValueError("public metric and stage-analysis arithmetic diverge")
        expected = _sha256(
            {
                "configuration_ids": self.configuration_ids,
                "generation_ids": self.generation_ids,
                "macro": asdict(self.macro),
                "micro": asdict(self.micro),
                "model_lock_artifact_ids": self.model_lock_artifact_ids,
                "observations": [asdict(item) for item in self.observations],
                "qrel_count": self.qrel_count,
                "query_count": self.query_count,
                "request_sha256": self.request_sha256,
                "schema_version": self.schema_version,
                "stage_analysis": asdict(self.stage_analysis),
                "worst_query_ids": self.worst_query_ids,
            }
        )
        if self.evidence_sha256 != expected:
            raise ValueError("public retrieval evaluation evidence identity mismatch")

    def manifest(self) -> dict[str, object]:
        """Return the stable compact JSON representation."""

        value = _json_value(asdict(self))
        assert isinstance(value, dict)
        return value


RetrievalQueryExecutor = Callable[
    [PublicRetrievalEvaluationRequest, ReviewedRetrievalQuery],
    RetrievalExecutionObservation,
]


class PublicRetrievalEvaluator:
    """Execute every reviewed query before computing any retrieval metric."""

    def __init__(self, execute: RetrievalQueryExecutor) -> None:
        self._execute = execute

    def evaluate(
        self, request: PublicRetrievalEvaluationRequest
    ) -> PublicRetrievalEvaluationReport:
        """Run the installed retriever and retain failures in the denominator."""

        observations = tuple(self._execute(request, query) for query in request.queries)
        for query, observation in zip(request.queries, observations, strict=True):
            if observation.query_id != query.query_id:
                raise PublicRetrievalEvaluationError(
                    "installed retrieval observation changed the query identity"
                )
            expected_query_sha256 = hashlib.sha256(
                query.query_text.encode("utf-8")
            ).hexdigest()
            if observation.query_text_sha256 != expected_query_sha256:
                raise PublicRetrievalEvaluationError(
                    "installed retrieval observation changed the query text"
                )
        cases = tuple(
            RetrievalEvaluationCase(
                query_id=query.query_id,
                input_identity_sha256=query.input_identity_sha256,
                qrels=tuple(
                    GradedQrel(item.chunk_id, item.relevance_grade)
                    for item in query.qrels
                ),
                hits=tuple(
                    RankedRetrievalHit(hit.chunk_id, 1.0 / hit.rank)
                    for hit in observation.hits
                ),
            )
            for query, observation in zip(request.queries, observations, strict=True)
        )
        macro = RetrievalMetricEvaluator().evaluate(cases)
        stage_analysis = aggregate_stage_analysis(
            tuple(
                analyze_query_stages(
                    query_id=query.query_id,
                    qrels=tuple(
                        (qrel.qrel_id, qrel.chunk_id, qrel.relevance_grade)
                        for qrel in query.qrels
                    ),
                    status=observation.status.value,
                    stages=observation.stages,
                    final_ranks=tuple(
                        (hit.chunk_id, hit.rank) for hit in observation.hits
                    ),
                )
                for query, observation in zip(
                    request.queries, observations, strict=True
                )
            )
        )
        relevant_qrels = sum(query.recall_at_5_denominator for query in macro.queries)
        retrieved_relevant = sum(query.recall_at_5_numerator for query in macro.queries)
        micro = PooledRetrievalCounts(
            relevant_qrels=relevant_qrels,
            retrieved_relevant_at_5=retrieved_relevant,
            recall_at_5=retrieved_relevant / relevant_qrels,
            total_ranked_hits=sum(len(item.hits) for item in observations),
            refused_queries=sum(
                item.status is RetrievalExecutionStatus.refused for item in observations
            ),
            failed_queries=sum(
                item.status is RetrievalExecutionStatus.failed for item in observations
            ),
        )
        metric_by_query = {item.query_id: item for item in macro.queries}
        worst = tuple(
            sorted(
                metric_by_query,
                key=lambda query_id: (
                    metric_by_query[query_id].recall_at_5,
                    metric_by_query[query_id].reciprocal_rank_at_10,
                    metric_by_query[query_id].ndcg_at_10,
                    query_id,
                ),
            )[: min(5, len(metric_by_query))]
        )
        schema_version = "bijux.canon.index.public-retrieval-evaluation.v2"
        configuration_ids = tuple(
            sorted({item.configuration_id for item in observations})
        )
        generation_ids = tuple(sorted({item.generation_id for item in observations}))
        model_lock_artifact_ids = tuple(
            sorted({item.model_lock_artifact_id for item in observations})
        )
        payload = {
            "configuration_ids": configuration_ids,
            "generation_ids": generation_ids,
            "macro": asdict(macro),
            "micro": asdict(micro),
            "model_lock_artifact_ids": model_lock_artifact_ids,
            "observations": [asdict(item) for item in observations],
            "qrel_count": sum(len(item.qrels) for item in request.queries),
            "query_count": len(request.queries),
            "request_sha256": request.request_sha256,
            "schema_version": schema_version,
            "stage_analysis": asdict(stage_analysis),
            "worst_query_ids": worst,
        }
        return PublicRetrievalEvaluationReport(
            schema_version=schema_version,
            request_sha256=request.request_sha256,
            query_count=len(request.queries),
            qrel_count=sum(len(item.qrels) for item in request.queries),
            generation_ids=generation_ids,
            model_lock_artifact_ids=model_lock_artifact_ids,
            configuration_ids=configuration_ids,
            observations=observations,
            macro=macro,
            micro=micro,
            stage_analysis=stage_analysis,
            worst_query_ids=worst,
            evidence_sha256=_sha256(payload),
        )


def load_reviewed_retrieval_request(
    *,
    cases_path: str | Path,
    qrels_path: str | Path,
    index_artifact_id: str,
    split: str = "development",
    mode: PublicRetrievalMode = PublicRetrievalMode.hybrid_ann,
    top_k: int = 10,
) -> PublicRetrievalEvaluationRequest:
    """Load source-reviewed labels while rejecting rankings in truth inputs."""

    cases = _jsonl(Path(cases_path), "evaluation cases")
    qrel_records = _jsonl(Path(qrels_path), "retrieval qrels")
    for record in (*cases, *qrel_records):
        forbidden = {"hits", "ranked_hits", "retrieved_qrel_ids"} & set(record)
        if forbidden:
            raise PublicRetrievalEvaluationError(
                f"evaluation truth must not contain supplied retrieval hits: {sorted(forbidden)}"
            )
    qrels_by_id: dict[str, Mapping[str, object]] = {}
    for record in qrel_records:
        qrel_id = record.get("qrel_id")
        if not isinstance(qrel_id, str) or not qrel_id or qrel_id in qrels_by_id:
            raise PublicRetrievalEvaluationError(
                "retrieval qrel identities must be present and unique"
            )
        if (
            record.get("schema_version") != "bijux.canon.research_qrel.v1"
            or record.get("adjudication_status") != "primary_review_complete"
            or record.get("system_ranking_consulted") is not False
        ):
            raise PublicRetrievalEvaluationError(
                f"retrieval qrel is not source-first reviewed: {qrel_id}"
            )
        qrels_by_id[qrel_id] = record
    selected = [record for record in cases if record.get("split") == split]
    if not selected:
        raise PublicRetrievalEvaluationError(
            f"evaluation split has no runnable reviewed cases: {split}"
        )
    queries: list[ReviewedRetrievalQuery] = []
    for case in selected:
        if (
            case.get("schema_version") != "bijux.canon.research_evaluation_case.v2"
            or case.get("system_output_consulted") is not False
            or case.get("system_output_may_define_truth") is not False
        ):
            raise PublicRetrievalEvaluationError(
                "evaluation case review policy is invalid"
            )
        truth = case.get("truth")
        if not isinstance(truth, dict):
            raise PublicRetrievalEvaluationError(
                "sealed evaluation labels require the authorized release evaluator"
            )
        raw_evidence = truth.get("evidence")
        if not isinstance(raw_evidence, list) or not raw_evidence:
            raise PublicRetrievalEvaluationError("evaluation case evidence is missing")
        reviewed: list[ReviewedRetrievalQrel] = []
        for edge in raw_evidence:
            if not isinstance(edge, dict):
                raise PublicRetrievalEvaluationError(
                    "evaluation evidence edge is invalid"
                )
            qrel_id = edge.get("qrel_id")
            qrel_record = qrels_by_id.get(str(qrel_id))
            if qrel_record is None:
                raise PublicRetrievalEvaluationError(
                    f"evaluation evidence references an unknown qrel: {qrel_id}"
                )
            chunk = qrel_record.get("chunk")
            if not isinstance(chunk, dict):
                raise PublicRetrievalEvaluationError("reviewed qrel chunk is invalid")
            reviewed.append(
                ReviewedRetrievalQrel(
                    qrel_id=str(qrel_id),
                    chunk_id=_required_string(chunk, "chunk_id"),
                    relevance_grade=_required_grade(edge),
                    relation=_required_string(edge, "relation"),
                    qrel_identity_sha256=_required_sha256(
                        qrel_record, "qrel_identity_sha256"
                    ),
                )
            )
        query_id = _required_string(case, "question_id")
        query_text = _required_string(case, "question")
        input_identity = _sha256(
            {
                "case_identity_sha256": _required_sha256(
                    case, "record_identity_sha256"
                ),
                "qrels": [asdict(item) for item in reviewed],
                "query_id": query_id,
                "query_text": query_text,
                "split": split,
                "truth_sha256": _required_sha256(case, "truth_sha256"),
            }
        )
        queries.append(
            ReviewedRetrievalQuery(
                query_id=query_id,
                query_text=query_text,
                input_identity_sha256=input_identity,
                qrels=tuple(reviewed),
            )
        )
    queries.sort(key=lambda item: item.query_id)
    return PublicRetrievalEvaluationRequest.create(
        index_artifact_id=index_artifact_id,
        split=split,
        mode=mode,
        top_k=top_k,
        queries=tuple(queries),
    )


def _jsonl(path: Path, label: str) -> tuple[Mapping[str, object], ...]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        records = tuple(json.loads(line) for line in lines if line.strip())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PublicRetrievalEvaluationError(f"{label} are unreadable") from error
    if not records or any(not isinstance(record, dict) for record in records):
        raise PublicRetrievalEvaluationError(f"{label} must be non-empty JSON objects")
    return records


def _required_string(value: Mapping[str, object], field: str) -> str:
    selected = value.get(field)
    if not isinstance(selected, str) or not selected.strip():
        raise PublicRetrievalEvaluationError(f"required text field is invalid: {field}")
    return selected


def _required_sha256(value: Mapping[str, object], field: str) -> str:
    selected = _required_string(value, field)
    if not _is_sha256(selected):
        raise PublicRetrievalEvaluationError(
            f"required SHA-256 field is invalid: {field}"
        )
    return selected


def _required_grade(value: Mapping[str, object]) -> int:
    selected = value.get("relevance_grade")
    if (
        isinstance(selected, bool)
        or not isinstance(selected, int)
        or not 0 <= selected <= 3
    ):
        raise PublicRetrievalEvaluationError("relevance grade must be within 0..3")
    return selected


def _json_value(value: object) -> object:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_value(item) for item in value]
    return value


def _sha256(value: object) -> str:
    content = json.dumps(
        _json_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _is_artifact_id(value: str) -> bool:
    return value.startswith("sha256:") and _is_sha256(value.removeprefix("sha256:"))


__all__ = [
    "ObservedLocatorSegment",
    "ObservedRetrievalHit",
    "PooledRetrievalCounts",
    "PublicRetrievalEvaluationError",
    "PublicRetrievalEvaluationReport",
    "PublicRetrievalEvaluationRequest",
    "PublicRetrievalEvaluator",
    "PublicRetrievalMode",
    "RetrievalExecutionObservation",
    "RetrievalExecutionStatus",
    "ReviewedRetrievalQrel",
    "ReviewedRetrievalQuery",
    "load_reviewed_retrieval_request",
]
