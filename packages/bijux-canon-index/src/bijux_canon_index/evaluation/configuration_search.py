# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Development-only retrieval configuration search over observed public evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math

from bijux_canon_index.evaluation.public_path import (
    PublicRetrievalEvaluationRequest,
    RetrievalExecutionObservation,
    RetrievalExecutionStatus,
)
from bijux_canon_index.evaluation.retrieval_metrics import (
    GradedQrel,
    RankedRetrievalHit,
    RetrievalEvaluationCase,
    RetrievalEvaluationReport,
    RetrievalMetricEvaluator,
)


class RetrievalConfigurationSearchError(ValueError):
    """The search input could leak held-out truth or hide observed failures."""


def _sha256(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class RetrievalSearchConfiguration:
    """One general weighted-RRF configuration; identities are never features."""

    candidate_depth: int
    lexical_admission_limit: int
    dense_admission_limit: int
    rank_constant: int
    lexical_weight: float
    dense_weight: float
    top_k: int = 10

    def __post_init__(self) -> None:
        if not 10 <= self.top_k <= self.candidate_depth <= 1000:
            raise ValueError("search bounds require 10 <= top_k <= candidate depth")
        if not self.top_k <= self.lexical_admission_limit <= self.candidate_depth:
            raise ValueError("lexical admission must include the output bound")
        if not self.top_k <= self.dense_admission_limit <= self.candidate_depth:
            raise ValueError("dense admission must include the output bound")
        if not 1 <= self.rank_constant <= 10_000:
            raise ValueError("search RRF rank constant must be within 1..10000")
        if any(
            not math.isfinite(value) or value <= 0
            for value in (self.lexical_weight, self.dense_weight)
        ):
            raise ValueError("search channel weights must be finite and positive")

    @property
    def configuration_id(self) -> str:
        """Return the content identity of all ranking-affecting parameters."""

        return f"sha256:{_sha256(asdict(self))}"


@dataclass(frozen=True, slots=True)
class ObservedFinalizationConfiguration:
    """Installed evidence-planning policy replayed from observed final ranks."""

    policy_sha256: str
    top_k: int = 10
    ranking_strategy: str = "installed-evidence-planning"

    def __post_init__(self) -> None:
        if (
            len(self.policy_sha256) != 64
            or any(
                character not in "0123456789abcdef" for character in self.policy_sha256
            )
            or not 10 <= self.top_k <= 1000
            or self.ranking_strategy != "installed-evidence-planning"
        ):
            raise ValueError("observed finalization configuration is invalid")

    @property
    def configuration_id(self) -> str:
        """Return the content identity of the installed finalization behavior."""

        return f"sha256:{_sha256(asdict(self))}"


RetrievalConfiguration = (
    RetrievalSearchConfiguration | ObservedFinalizationConfiguration
)


@dataclass(frozen=True, slots=True)
class RetrievalQualityFloor:
    """Immutable metric floor applied without weakening during search."""

    recall_at_5: float = 0.90
    mrr_at_10: float = 0.85
    ndcg_at_10: float = 0.85

    def __post_init__(self) -> None:
        if any(
            not math.isfinite(value) or not 0 <= value <= 1
            for value in (self.recall_at_5, self.mrr_at_10, self.ndcg_at_10)
        ):
            raise ValueError("retrieval quality floors must be within zero and one")


@dataclass(frozen=True, slots=True)
class RetrievalConfigurationResult:
    """Metrics and per-query tradeoffs for one searched configuration."""

    configuration: RetrievalConfiguration
    metrics: RetrievalEvaluationReport
    meets_floor: bool
    failed_metrics: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RetrievalConfigurationSearchReport:
    """Integrity-bound ranking search using development observations only."""

    schema_version: str
    split: str
    query_count: int
    qrel_count: int
    quality_floor: RetrievalQualityFloor
    results: tuple[RetrievalConfigurationResult, ...]
    selected_configuration_id: str | None
    evidence_sha256: str

    def __post_init__(self) -> None:
        if self.schema_version != "bijux.canon.index.retrieval-config-search.v1":
            raise ValueError("retrieval configuration search schema is unsupported")
        if self.split != "development":
            raise ValueError("retrieval configuration search is development-only")
        if self.query_count < 1 or self.qrel_count < 1 or not self.results:
            raise ValueError("retrieval configuration search denominators are invalid")
        identities = tuple(
            result.configuration.configuration_id for result in self.results
        )
        if len(identities) != len(set(identities)):
            raise ValueError("retrieval search configurations must be unique")
        passing = tuple(
            result.configuration.configuration_id
            for result in self.results
            if result.meets_floor
        )
        if self.selected_configuration_id is not None and (
            not passing or self.selected_configuration_id != passing[0]
        ):
            raise ValueError("selected retrieval configuration is not the first pass")
        expected = _sha256(
            {
                "qrel_count": self.qrel_count,
                "quality_floor": asdict(self.quality_floor),
                "query_count": self.query_count,
                "results": [asdict(result) for result in self.results],
                "schema_version": self.schema_version,
                "selected_configuration_id": self.selected_configuration_id,
                "split": self.split,
            }
        )
        if self.evidence_sha256 != expected:
            raise ValueError("retrieval configuration search identity mismatch")


_DEFAULT_RETRIEVAL_QUALITY_FLOOR = RetrievalQualityFloor()


def search_retrieval_configurations(
    *,
    request: PublicRetrievalEvaluationRequest,
    observations: tuple[RetrievalExecutionObservation, ...],
    configurations: tuple[RetrievalConfiguration, ...],
    quality_floor: RetrievalQualityFloor = _DEFAULT_RETRIEVAL_QUALITY_FLOOR,
) -> RetrievalConfigurationSearchReport:
    """Rerank observed channel evidence without rerunning or consulting held-out truth."""

    if request.split != "development":
        raise RetrievalConfigurationSearchError(
            "retrieval configuration search may only use development truth"
        )
    if len(observations) != len(request.queries):
        raise RetrievalConfigurationSearchError(
            "retrieval configuration search cannot change the query denominator"
        )
    if not configurations:
        raise RetrievalConfigurationSearchError(
            "retrieval configuration search requires candidate configurations"
        )
    by_query = {observation.query_id: observation for observation in observations}
    if len(by_query) != len(observations) or set(by_query) != {
        query.query_id for query in request.queries
    }:
        raise RetrievalConfigurationSearchError(
            "retrieval configuration search observations changed query identities"
        )
    results = tuple(
        _evaluate_configuration(
            request=request,
            by_query=by_query,
            configuration=configuration,
            quality_floor=quality_floor,
        )
        for configuration in configurations
    )
    selected = next(
        (
            result.configuration.configuration_id
            for result in results
            if result.meets_floor
        ),
        None,
    )
    schema_version = "bijux.canon.index.retrieval-config-search.v1"
    qrel_count = sum(len(query.qrels) for query in request.queries)
    payload = {
        "qrel_count": qrel_count,
        "quality_floor": asdict(quality_floor),
        "query_count": len(request.queries),
        "results": [asdict(result) for result in results],
        "schema_version": schema_version,
        "selected_configuration_id": selected,
        "split": request.split,
    }
    return RetrievalConfigurationSearchReport(
        schema_version=schema_version,
        split=request.split,
        query_count=len(request.queries),
        qrel_count=qrel_count,
        quality_floor=quality_floor,
        results=results,
        selected_configuration_id=selected,
        evidence_sha256=_sha256(payload),
    )


def _evaluate_configuration(
    *,
    request: PublicRetrievalEvaluationRequest,
    by_query: dict[str, RetrievalExecutionObservation],
    configuration: RetrievalConfiguration,
    quality_floor: RetrievalQualityFloor,
) -> RetrievalConfigurationResult:
    cases = []
    for query in request.queries:
        observation = by_query[query.query_id]
        ranked = (
            ()
            if observation.status
            in {RetrievalExecutionStatus.refused, RetrievalExecutionStatus.failed}
            else _rerank(observation, configuration)
        )
        cases.append(
            RetrievalEvaluationCase(
                query_id=query.query_id,
                input_identity_sha256=query.input_identity_sha256,
                qrels=tuple(
                    GradedQrel(qrel.chunk_id, qrel.relevance_grade)
                    for qrel in query.qrels
                ),
                hits=tuple(
                    RankedRetrievalHit(chunk_id, score) for chunk_id, score in ranked
                ),
            )
        )
    metrics = RetrievalMetricEvaluator().evaluate(tuple(cases))
    values = {metric.metric_id: metric.value for metric in metrics.metrics}
    failed = tuple(
        metric_id
        for metric_id, floor in (
            ("recall-at-5", quality_floor.recall_at_5),
            ("mrr-at-10", quality_floor.mrr_at_10),
            ("ndcg-at-10", quality_floor.ndcg_at_10),
        )
        if values[metric_id] < floor
    )
    return RetrievalConfigurationResult(
        configuration=configuration,
        metrics=metrics,
        meets_floor=not failed,
        failed_metrics=failed,
    )


def _rerank(
    observation: RetrievalExecutionObservation,
    configuration: RetrievalConfiguration,
) -> tuple[tuple[str, float], ...]:
    if isinstance(configuration, ObservedFinalizationConfiguration):
        stages = observation.stages
        if stages is None or stages.rerank_policy_sha256 != configuration.policy_sha256:
            raise RetrievalConfigurationSearchError(
                "observed finalization configuration differs from installed evidence"
            )
        return tuple(
            (candidate.chunk_id, 1.0 / candidate.source_rank)
            for candidate in stages.rerank_candidates[: configuration.top_k]
        )
    stages = observation.stages
    if stages is None or stages.dense_outcome is None:
        raise RetrievalConfigurationSearchError(
            "hybrid configuration search requires observed lexical and dense stages"
        )
    lexical = {
        candidate.chunk_id: candidate
        for candidate in stages.lexical_candidates
        if candidate.source_rank <= configuration.candidate_depth
        and candidate.source_rank <= configuration.lexical_admission_limit
    }
    dense = {
        candidate.chunk_id: candidate
        for candidate in stages.dense_candidates
        if candidate.source_rank <= configuration.candidate_depth
        and candidate.source_rank <= configuration.dense_admission_limit
    }
    scores = {
        chunk_id: configuration.lexical_weight
        / (configuration.rank_constant + candidate.source_rank)
        for chunk_id, candidate in lexical.items()
    }
    for chunk_id, candidate in dense.items():
        scores[chunk_id] = scores.get(chunk_id, 0.0) + (
            configuration.dense_weight
            / (configuration.rank_constant + candidate.source_rank)
        )
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return tuple(ordered[: configuration.top_k])


def default_retrieval_search_configurations(
    *,
    observed_candidate_depth: int,
    top_k: int = 10,
) -> tuple[RetrievalSearchConfiguration, ...]:
    """Return a small, ordered, identity-free development search space."""

    if not top_k <= observed_candidate_depth <= 1000:
        raise ValueError("observed candidate depth must include the output bound")
    depths = tuple(
        sorted(
            {
                min(observed_candidate_depth, depth)
                for depth in (40, 80, 150, 500, observed_candidate_depth)
                if min(observed_candidate_depth, depth) >= top_k
            }
        )
    )
    configurations = []
    for depth in depths:
        for lexical_limit in tuple(dict.fromkeys((top_k, depth))):
            for rank_constant in (60, 10, 1):
                for lexical_weight, dense_weight in (
                    (1.0, 1.0),
                    (1.0, 2.0),
                    (2.0, 1.0),
                ):
                    configurations.append(
                        RetrievalSearchConfiguration(
                            candidate_depth=depth,
                            lexical_admission_limit=lexical_limit,
                            dense_admission_limit=depth,
                            rank_constant=rank_constant,
                            lexical_weight=lexical_weight,
                            dense_weight=dense_weight,
                            top_k=top_k,
                        )
                    )
    return tuple(configurations)


def observed_finalization_search_configuration(
    observations: tuple[RetrievalExecutionObservation, ...],
    *,
    top_k: int = 10,
) -> ObservedFinalizationConfiguration:
    """Bind one search candidate to the installed policy without consulting qrels."""

    policies = {
        observation.stages.rerank_policy_sha256
        for observation in observations
        if observation.stages is not None
        and observation.stages.rerank_policy_sha256 is not None
    }
    if len(policies) != 1:
        raise RetrievalConfigurationSearchError(
            "installed observations require one finalization policy identity"
        )
    return ObservedFinalizationConfiguration(policies.pop(), top_k=top_k)


__all__ = [
    "RetrievalConfigurationResult",
    "RetrievalConfigurationSearchError",
    "RetrievalConfigurationSearchReport",
    "RetrievalQualityFloor",
    "RetrievalSearchConfiguration",
    "ObservedFinalizationConfiguration",
    "default_retrieval_search_configurations",
    "observed_finalization_search_configuration",
    "search_retrieval_configurations",
]
