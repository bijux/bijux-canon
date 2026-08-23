# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Relevant-evidence lineage across installed retrieval stages."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
import math


class RetrievalDiagnosticError(ValueError):
    """Observed stage evidence is incomplete or violates candidate conservation."""


class RetrievalStage(StrEnum):
    """Ordered installed retrieval stages visible to quality analysis."""

    lexical = "lexical"
    dense = "dense"
    fusion = "fusion"


class RelevantEvidenceDisposition(StrEnum):
    """First accountable outcome for one reviewed relevant chunk."""

    retained_at_5 = "retained_at_5"
    final_below_5 = "final_below_5"
    absent_from_candidate_depth = "absent_from_candidate_depth"
    excluded_by_channel_limit = "excluded_by_channel_limit"
    lost_at_fusion_limit = "lost_at_fusion_limit"
    lost_at_finalization = "lost_at_finalization"
    execution_refused = "execution_refused"
    execution_failed = "execution_failed"


@dataclass(frozen=True, slots=True)
class ObservedStageCandidate:
    """One raw candidate rank retained from an installed retrieval stage."""

    stage: RetrievalStage
    chunk_id: str
    source_rank: int
    output_rank: int | None
    score: float
    disposition: str

    def __post_init__(self) -> None:
        if not self.chunk_id.strip() or not self.disposition.strip():
            raise ValueError("retrieval stage candidate identity is incomplete")
        if self.source_rank < 1 or (
            self.output_rank is not None and self.output_rank < 1
        ):
            raise ValueError("retrieval stage candidate ranks must be positive")
        if not math.isfinite(self.score):
            raise ValueError("retrieval stage candidate score must be finite")


@dataclass(frozen=True, slots=True)
class RetrievalStageEvidence:
    """Raw lexical, dense, and fusion evidence for one installed query."""

    lexical_outcome: str
    dense_outcome: str | None
    fusion_policy_sha256: str | None
    lexical_candidates: tuple[ObservedStageCandidate, ...]
    dense_candidates: tuple[ObservedStageCandidate, ...]
    fusion_candidates: tuple[ObservedStageCandidate, ...]

    def __post_init__(self) -> None:
        if not self.lexical_outcome.strip():
            raise ValueError("retrieval stage evidence requires a lexical outcome")
        if self.dense_outcome is not None and not self.dense_outcome.strip():
            raise ValueError("retrieval dense outcome must not be empty")
        expected = (
            (RetrievalStage.lexical, self.lexical_candidates),
            (RetrievalStage.dense, self.dense_candidates),
            (RetrievalStage.fusion, self.fusion_candidates),
        )
        for stage, candidates in expected:
            if any(candidate.stage is not stage for candidate in candidates):
                raise ValueError("retrieval stage candidate is in the wrong channel")
            chunk_ids = tuple(candidate.chunk_id for candidate in candidates)
            ranks = tuple(candidate.source_rank for candidate in candidates)
            if len(chunk_ids) != len(set(chunk_ids)):
                raise ValueError("retrieval stage candidate identities must be unique")
            if ranks != tuple(range(1, len(ranks) + 1)):
                raise ValueError("retrieval stage source ranks must be contiguous")
        lexical_included = tuple(
            candidate.output_rank
            for candidate in self.lexical_candidates
            if candidate.output_rank is not None
        )
        if lexical_included != tuple(range(1, len(lexical_included) + 1)):
            raise ValueError("lexical output ranks must be contiguous")
        hybrid = self.dense_outcome is not None
        if hybrid != (self.fusion_policy_sha256 is not None):
            raise ValueError("hybrid retrieval requires a fusion policy identity")
        if not hybrid and (self.dense_candidates or self.fusion_candidates):
            raise ValueError(
                "lexical retrieval cannot retain dense or fusion candidates"
            )


@dataclass(frozen=True, slots=True)
class RelevantEvidenceStageTrace:
    """Every observed rank and first loss point for one reviewed qrel."""

    qrel_id: str
    chunk_id: str
    relevance_grade: int
    lexical_source_rank: int | None
    lexical_output_rank: int | None
    lexical_disposition: str | None
    dense_rank: int | None
    fusion_rank: int | None
    final_rank: int | None
    disposition: RelevantEvidenceDisposition

    def __post_init__(self) -> None:
        if not self.qrel_id.strip() or not self.chunk_id.strip():
            raise ValueError("relevant-evidence trace identity is incomplete")
        if isinstance(self.relevance_grade, bool) or not 0 <= self.relevance_grade <= 3:
            raise ValueError("relevant-evidence trace grade must be within 0..3")


@dataclass(frozen=True, slots=True)
class QueryStageDiagnostics:
    """Candidate conservation and relevant-evidence losses for one question."""

    query_id: str
    lexical_observed_count: int
    lexical_included_count: int
    dense_observed_count: int
    fusion_count: int
    final_count: int
    relevant_evidence: tuple[RelevantEvidenceStageTrace, ...]

    def __post_init__(self) -> None:
        if not self.query_id.strip() or not self.relevant_evidence:
            raise ValueError("query stage diagnostics require identity and qrels")
        if (
            min(
                self.lexical_observed_count,
                self.lexical_included_count,
                self.dense_observed_count,
                self.fusion_count,
                self.final_count,
            )
            < 0
        ):
            raise ValueError("query stage candidate counts must be non-negative")
        if self.lexical_included_count > self.lexical_observed_count:
            raise ValueError("lexical included count exceeds observed candidates")
        qrel_ids = tuple(item.qrel_id for item in self.relevant_evidence)
        if len(qrel_ids) != len(set(qrel_ids)):
            raise ValueError("query stage qrel identities must be unique")


@dataclass(frozen=True, slots=True)
class RelevantStageRecall:
    """Exact reviewed-qrel recall at one retrieval boundary."""

    stage_id: str
    numerator: int
    denominator: int
    value: float

    def __post_init__(self) -> None:
        if not self.stage_id.strip() or not 0 <= self.numerator <= self.denominator:
            raise ValueError("stage recall arithmetic is invalid")
        if self.denominator < 1 or not math.isclose(
            self.value, self.numerator / self.denominator
        ):
            raise ValueError("stage recall value differs from its arithmetic")


@dataclass(frozen=True, slots=True)
class RetrievalStageAnalysis:
    """Compact failure population across all reviewed question-evidence pairs."""

    schema_version: str
    query_count: int
    qrel_count: int
    recall: tuple[RelevantStageRecall, ...]
    disposition_counts: tuple[tuple[str, int], ...]
    queries: tuple[QueryStageDiagnostics, ...]

    def __post_init__(self) -> None:
        if self.schema_version != "bijux.canon.index.retrieval-stage-analysis.v1":
            raise ValueError("retrieval stage analysis schema is unsupported")
        if self.query_count != len(self.queries) or self.query_count < 1:
            raise ValueError("retrieval stage query denominator is invalid")
        observed_qrels = sum(len(query.relevant_evidence) for query in self.queries)
        if self.qrel_count != observed_qrels or self.qrel_count < 1:
            raise ValueError("retrieval stage qrel denominator is invalid")
        if sum(count for _, count in self.disposition_counts) != self.qrel_count:
            raise ValueError("retrieval stage disposition counts hide qrels")
        if tuple(sorted(self.disposition_counts)) != self.disposition_counts:
            raise ValueError("retrieval stage dispositions must be sorted")
        if tuple(item.stage_id for item in self.recall) != (
            "candidate-depth",
            "channel-admitted",
            "fusion-at-10",
            "final-at-10",
            "final-at-5",
        ):
            raise ValueError("retrieval stage recall boundaries are incomplete")
        if any(item.denominator != self.qrel_count for item in self.recall):
            raise ValueError("retrieval stage recall denominators diverge")


def analyze_query_stages(
    *,
    query_id: str,
    qrels: tuple[tuple[str, str, int], ...],
    status: str,
    stages: RetrievalStageEvidence | None,
    final_ranks: tuple[tuple[str, int], ...],
) -> QueryStageDiagnostics:
    """Classify every qrel after proving observed candidates were conserved."""

    if status in {"refused", "failed"}:
        if stages is not None or final_ranks:
            raise RetrievalDiagnosticError(
                "failed retrieval cannot claim successful stage candidates"
            )
        disposition = (
            RelevantEvidenceDisposition.execution_refused
            if status == "refused"
            else RelevantEvidenceDisposition.execution_failed
        )
        traces = tuple(_trace(qrel, disposition=disposition) for qrel in qrels)
        return QueryStageDiagnostics(query_id, 0, 0, 0, 0, 0, traces)
    if stages is None:
        raise RetrievalDiagnosticError(
            "usable retrieval requires raw stage evidence for diagnosis"
        )

    lexical = {candidate.chunk_id: candidate for candidate in stages.lexical_candidates}
    dense = {candidate.chunk_id: candidate for candidate in stages.dense_candidates}
    fusion = {candidate.chunk_id: candidate for candidate in stages.fusion_candidates}
    final = dict(final_ranks)
    if len(final) != len(final_ranks):
        raise RetrievalDiagnosticError("final retrieval identities must be unique")
    lexical_included = {
        chunk_id for chunk_id, candidate in lexical.items() if candidate.output_rank
    }
    if stages.dense_outcome is None:
        preceding = lexical_included
    else:
        preceding = lexical_included | set(dense)
        if not set(fusion).issubset(preceding):
            raise RetrievalDiagnosticError(
                "fusion contains a candidate absent from both input channels"
            )
    final_predecessors = set(fusion) if fusion else preceding
    if not set(final).issubset(final_predecessors):
        raise RetrievalDiagnosticError(
            "final retrieval contains a candidate absent from its prior stage"
        )

    traces = tuple(
        _classify_qrel(
            qrel=qrel,
            lexical=lexical,
            dense=dense,
            fusion=fusion,
            final=final,
        )
        for qrel in qrels
    )
    return QueryStageDiagnostics(
        query_id=query_id,
        lexical_observed_count=len(lexical),
        lexical_included_count=len(lexical_included),
        dense_observed_count=len(dense),
        fusion_count=len(fusion),
        final_count=len(final),
        relevant_evidence=traces,
    )


def aggregate_stage_analysis(
    queries: tuple[QueryStageDiagnostics, ...],
) -> RetrievalStageAnalysis:
    """Aggregate a stable disposition count without hiding any qrel."""

    if not queries:
        raise RetrievalDiagnosticError("stage analysis requires at least one query")
    query_ids = tuple(query.query_id for query in queries)
    if len(query_ids) != len(set(query_ids)):
        raise RetrievalDiagnosticError("stage analysis query identities must be unique")
    counter = Counter(
        trace.disposition.value
        for query in queries
        for trace in query.relevant_evidence
    )
    qrel_count = sum(len(query.relevant_evidence) for query in queries)
    traces = tuple(trace for query in queries for trace in query.relevant_evidence)
    recall = (
        _recall(
            "candidate-depth",
            sum(
                trace.lexical_source_rank is not None or trace.dense_rank is not None
                for trace in traces
            ),
            qrel_count,
        ),
        _recall(
            "channel-admitted",
            sum(
                trace.lexical_output_rank is not None or trace.dense_rank is not None
                for trace in traces
            ),
            qrel_count,
        ),
        _recall(
            "fusion-at-10",
            sum(
                trace.fusion_rank is not None and trace.fusion_rank <= 10
                for trace in traces
            ),
            qrel_count,
        ),
        _recall(
            "final-at-10",
            sum(
                trace.final_rank is not None and trace.final_rank <= 10
                for trace in traces
            ),
            qrel_count,
        ),
        _recall(
            "final-at-5",
            sum(
                trace.final_rank is not None and trace.final_rank <= 5
                for trace in traces
            ),
            qrel_count,
        ),
    )
    return RetrievalStageAnalysis(
        schema_version="bijux.canon.index.retrieval-stage-analysis.v1",
        query_count=len(queries),
        qrel_count=qrel_count,
        recall=recall,
        disposition_counts=tuple(sorted(counter.items())),
        queries=queries,
    )


def _recall(stage_id: str, numerator: int, denominator: int) -> RelevantStageRecall:
    return RelevantStageRecall(
        stage_id=stage_id,
        numerator=numerator,
        denominator=denominator,
        value=numerator / denominator,
    )


def _classify_qrel(
    *,
    qrel: tuple[str, str, int],
    lexical: dict[str, ObservedStageCandidate],
    dense: dict[str, ObservedStageCandidate],
    fusion: dict[str, ObservedStageCandidate],
    final: dict[str, int],
) -> RelevantEvidenceStageTrace:
    qrel_id, chunk_id, grade = qrel
    lexical_candidate = lexical.get(chunk_id)
    dense_candidate = dense.get(chunk_id)
    final_rank = final.get(chunk_id)
    if final_rank is not None:
        disposition = (
            RelevantEvidenceDisposition.retained_at_5
            if final_rank <= 5
            else RelevantEvidenceDisposition.final_below_5
        )
    elif chunk_id in fusion:
        disposition = RelevantEvidenceDisposition.lost_at_finalization
    elif (
        lexical_candidate is not None
        and lexical_candidate.output_rank is None
        and dense_candidate is None
    ):
        disposition = RelevantEvidenceDisposition.excluded_by_channel_limit
    elif lexical_candidate is not None or dense_candidate is not None:
        disposition = RelevantEvidenceDisposition.lost_at_fusion_limit
    else:
        disposition = RelevantEvidenceDisposition.absent_from_candidate_depth
    return _trace(
        qrel,
        lexical=lexical_candidate,
        dense=dense_candidate,
        fusion=fusion.get(chunk_id),
        final_rank=final_rank,
        disposition=disposition,
    )


def _trace(
    qrel: tuple[str, str, int],
    *,
    lexical: ObservedStageCandidate | None = None,
    dense: ObservedStageCandidate | None = None,
    fusion: ObservedStageCandidate | None = None,
    final_rank: int | None = None,
    disposition: RelevantEvidenceDisposition,
) -> RelevantEvidenceStageTrace:
    qrel_id, chunk_id, grade = qrel
    return RelevantEvidenceStageTrace(
        qrel_id=qrel_id,
        chunk_id=chunk_id,
        relevance_grade=grade,
        lexical_source_rank=None if lexical is None else lexical.source_rank,
        lexical_output_rank=None if lexical is None else lexical.output_rank,
        lexical_disposition=None if lexical is None else lexical.disposition,
        dense_rank=None if dense is None else dense.source_rank,
        fusion_rank=None if fusion is None else fusion.source_rank,
        final_rank=final_rank,
        disposition=disposition,
    )


__all__ = [
    "ObservedStageCandidate",
    "QueryStageDiagnostics",
    "RelevantStageRecall",
    "RelevantEvidenceDisposition",
    "RelevantEvidenceStageTrace",
    "RetrievalDiagnosticError",
    "RetrievalStage",
    "RetrievalStageAnalysis",
    "RetrievalStageEvidence",
    "aggregate_stage_analysis",
    "analyze_query_stages",
]
