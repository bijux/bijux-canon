# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Rank and fill research gaps within explicit value and resource bounds."""

from __future__ import annotations

from enum import StrEnum
import math
from typing import Literal, Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)
from bijux_canon_reason.research.assumptions_insufficiency import (
    ResearchDeficiency,
    ResearchDeficiencyStatus,
)
from bijux_canon_reason.research.gap_retrieval import (
    EvidenceChange,
    GapRetrievalPolicy,
    GapRetrievalRecord,
    GapRetrievalService,
    RetrievalEvidencePort,
    RetrievalTargetKind,
    ScopedRetrievalRequest,
    create_gap_retrieval_request,
)


class GapFillingSourceKind(StrEnum):
    """Graph artifact that opened a fillable evidence gap."""

    research_deficiency = "research_deficiency"
    counterevidence_candidate = "counterevidence_candidate"


class GapResolutionStatus(StrEnum):
    """Whether a candidate remains eligible for retrieval."""

    unresolved = "unresolved"
    resolved = "resolved"


class GapFillingDisposition(StrEnum):
    """Why one ranked gap was selected or stopped."""

    selected = "selected"
    already_resolved = "already_resolved"
    expected_value_below_threshold = "expected_value_below_threshold"
    request_budget = "request_budget"
    evidence_budget = "evidence_budget"
    query_budget = "query_budget"


class GapFillingStopReason(StrEnum):
    """Stable reason no additional gap was selected in this cycle."""

    candidates_exhausted = "candidates_exhausted"
    expected_value_floor = "expected_value_floor"
    request_budget = "request_budget"
    evidence_budget = "evidence_budget"
    query_budget = "query_budget"


class GapFillingErrorCode(StrEnum):
    """Stable planning failures before bounded retrieval begins."""

    duplicate_candidate = "duplicate_candidate"
    duplicate_gap = "duplicate_gap"
    mixed_graph_identity = "mixed_graph_identity"


class GapFillingError(ValueError):
    """A gap-filling plan cannot preserve deterministic ownership."""

    def __init__(self, code: GapFillingErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class GapFillingPolicy(StableModel):
    """Hard request, evidence-cost, result, and expected-value limits."""

    max_requests: int = 8
    evidence_cost_budget: int = 100
    max_evidence_per_request: int = 10
    max_query_characters: int = 4_096
    minimum_expected_value: float = 0.01

    @model_validator(mode="after")
    def _validate_bounds(self) -> Self:
        if not 1 <= self.max_requests <= 100:
            raise ValueError("gap-filling request budget must be within 1..100")
        if not 1 <= self.evidence_cost_budget <= 1_000_000:
            raise ValueError("evidence-cost budget must be within 1..1000000")
        if not 1 <= self.max_evidence_per_request <= 1_000:
            raise ValueError("per-request evidence limit must be within 1..1000")
        if not 1 <= self.max_query_characters <= 100_000:
            raise ValueError("gap-filling query bound must be within 1..100000")
        if (
            not math.isfinite(self.minimum_expected_value)
            or not 0 <= self.minimum_expected_value <= 1
        ):
            raise ValueError("minimum expected value must be finite and in [0,1]")
        return self


class GapFillingCandidate(StableModel):
    """One unresolved graph gap with explicit impact, likelihood, and cost."""

    artifact_id: str
    graph_artifact_id: str
    source_artifact_id: str
    source_kind: GapFillingSourceKind
    target_claim_artifact_id: str | None
    scope_artifact_id: str
    query_text: str
    rationale: str
    answer_impact: float
    resolution_probability: float
    evidence_cost: int
    status: GapResolutionStatus
    prior_evidence_artifact_ids: tuple[str, ...]

    @field_validator(
        "artifact_id",
        "graph_artifact_id",
        "source_artifact_id",
        "target_claim_artifact_id",
        "scope_artifact_id",
    )
    @classmethod
    def _validate_optional_artifact_id(cls, value: str | None) -> str | None:
        return None if value is None else require_artifact_id(value)

    @field_validator("query_text", "rationale")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("gap-filling query and rationale must not be empty")
        return normalized

    @field_validator("prior_evidence_artifact_ids")
    @classmethod
    def _validate_prior_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("prior gap evidence identities must be unique")
        return tuple(sorted(require_artifact_id(item) for item in value))

    @model_validator(mode="after")
    def _validate_candidate(self) -> Self:
        if any(
            not math.isfinite(value) or not 0 <= value <= 1
            for value in (self.answer_impact, self.resolution_probability)
        ):
            raise ValueError("gap impact and resolution probability must be in [0,1]")
        if self.evidence_cost <= 0:
            raise ValueError("gap evidence cost must be positive")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("gap-filling candidate identity does not match")
        return self

    @property
    def expected_value(self) -> float:
        """Return stable expected answer value per evidence-cost unit."""

        return round(
            self.answer_impact * self.resolution_probability / self.evidence_cost,
            12,
        )


class GapFillingDecision(StableModel):
    """Exact ranking and budget decision for one candidate."""

    candidate_artifact_id: str
    source_artifact_id: str
    rank: int
    expected_value: float
    evidence_cost: int
    disposition: GapFillingDisposition
    rationale: str
    request_artifact_id: str | None

    @field_validator(
        "candidate_artifact_id", "source_artifact_id", "request_artifact_id"
    )
    @classmethod
    def _validate_optional_artifact_id(cls, value: str | None) -> str | None:
        return None if value is None else require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_decision(self) -> Self:
        if self.rank <= 0 or self.evidence_cost <= 0:
            raise ValueError("gap-filling decision rank and cost must be positive")
        if not math.isfinite(self.expected_value) or self.expected_value < 0:
            raise ValueError(
                "gap-filling expected value must be finite and nonnegative"
            )
        if not self.rationale:
            raise ValueError("gap-filling decisions require a rationale")
        if (self.disposition is GapFillingDisposition.selected) != (
            self.request_artifact_id is not None
        ):
            raise ValueError("only selected gaps may expose a retrieval request")
        return self


class GapFillingPlan(StableModel):
    """Content-addressed value ordering and bounded retrieval requests."""

    schema_version: Literal["bijux.canon.reason.gap_filling_plan.v1"] = (
        "bijux.canon.reason.gap_filling_plan.v1"
    )
    artifact_id: str
    graph_artifact_id: str
    policy: GapFillingPolicy
    requests: tuple[ScopedRetrievalRequest, ...]
    decisions: tuple[GapFillingDecision, ...]
    projected_evidence_cost: int
    stop_reasons: tuple[GapFillingStopReason, ...]

    @field_validator("artifact_id", "graph_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_plan(self) -> Self:
        selected_ids = tuple(
            item.request_artifact_id
            for item in self.decisions
            if item.disposition is GapFillingDisposition.selected
        )
        if selected_ids != tuple(item.artifact_id for item in self.requests):
            raise ValueError("gap-filling decisions must match ordered requests")
        if len(self.requests) > self.policy.max_requests:
            raise ValueError("gap-filling plan exceeds its request budget")
        if self.projected_evidence_cost > self.policy.evidence_cost_budget:
            raise ValueError("gap-filling plan exceeds its evidence-cost budget")
        if self.projected_evidence_cost != sum(
            item.evidence_cost
            for item in self.decisions
            if item.disposition is GapFillingDisposition.selected
        ):
            raise ValueError("projected evidence cost must match selected decisions")
        if tuple(sorted(set(self.stop_reasons))) != self.stop_reasons:
            raise ValueError("gap-filling stop reasons must be unique and sorted")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("gap-filling plan identity does not match")
        return self


class GapFillingExecutionRecord(StableModel):
    """Evidence delta produced for one selected high-value gap."""

    artifact_id: str
    candidate_artifact_id: str
    source_artifact_id: str
    request_artifact_id: str
    retrieval_record_artifact_id: str
    change: EvidenceChange
    added_evidence_artifact_ids: tuple[str, ...]

    @field_validator(
        "artifact_id",
        "candidate_artifact_id",
        "source_artifact_id",
        "request_artifact_id",
        "retrieval_record_artifact_id",
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("added_evidence_artifact_ids")
    @classmethod
    def _validate_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("gap-filling evidence identities must be unique")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_record(self) -> Self:
        if (self.change is EvidenceChange.evidence_added) != bool(
            self.added_evidence_artifact_ids
        ):
            raise ValueError("gap-filling evidence change does not match its delta")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("gap-filling execution identity does not match")
        return self


class GapFillingRun(StableModel):
    """Closed gap-filling cycle, including a value-only stopping decision."""

    schema_version: Literal["bijux.canon.reason.gap_filling_run.v1"] = (
        "bijux.canon.reason.gap_filling_run.v1"
    )
    artifact_id: str
    plan_artifact_id: str
    retrieval_run_artifact_id: str | None
    records: tuple[GapFillingExecutionRecord, ...]
    stop_reasons: tuple[GapFillingStopReason, ...]

    @field_validator("artifact_id", "plan_artifact_id", "retrieval_run_artifact_id")
    @classmethod
    def _validate_optional_artifact_id(cls, value: str | None) -> str | None:
        return None if value is None else require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_run(self) -> Self:
        if bool(self.records) != (self.retrieval_run_artifact_id is not None):
            raise ValueError(
                "gap-filling retrieval identity must match execution records"
            )
        if tuple(sorted(set(self.stop_reasons))) != self.stop_reasons:
            raise ValueError("gap-filling run stop reasons must be unique and sorted")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("gap-filling run identity does not match")
        return self


class GapFillingService:
    """Greedily select the highest expected-value gaps within hard budgets."""

    def __init__(self, policy: GapFillingPolicy | None = None) -> None:
        self.policy = policy or GapFillingPolicy()

    def plan(self, candidates: tuple[GapFillingCandidate, ...]) -> GapFillingPlan:
        """Rank all candidates and explain every selection or stopping decision."""

        candidate_ids = tuple(item.artifact_id for item in candidates)
        if len(candidate_ids) != len(set(candidate_ids)):
            raise GapFillingError(
                GapFillingErrorCode.duplicate_candidate,
                "gap-filling candidate identities must be unique",
            )
        source_ids = tuple(item.source_artifact_id for item in candidates)
        if len(source_ids) != len(set(source_ids)):
            raise GapFillingError(
                GapFillingErrorCode.duplicate_gap,
                "one gap-filling cycle may assess each source gap once",
            )
        graph_ids = {item.graph_artifact_id for item in candidates}
        if len(graph_ids) > 1:
            raise GapFillingError(
                GapFillingErrorCode.mixed_graph_identity,
                "gap-filling candidates cannot mix graph revisions",
            )
        ordered = tuple(
            sorted(
                candidates,
                key=lambda item: (
                    -item.expected_value,
                    -item.answer_impact,
                    item.evidence_cost,
                    item.artifact_id,
                ),
            )
        )
        requests: list[ScopedRetrievalRequest] = []
        decisions: list[GapFillingDecision] = []
        spent = 0
        for rank, candidate in enumerate(ordered, start=1):
            request = None
            if candidate.status is GapResolutionStatus.resolved:
                disposition = GapFillingDisposition.already_resolved
                rationale = (
                    "gap is already resolved and cannot consume retrieval budget"
                )
            elif len(candidate.query_text) > self.policy.max_query_characters:
                disposition = GapFillingDisposition.query_budget
                rationale = "gap query exceeds the configured character budget"
            elif candidate.expected_value < self.policy.minimum_expected_value:
                disposition = GapFillingDisposition.expected_value_below_threshold
                rationale = "expected answer value is below the configured floor"
            elif len(requests) >= self.policy.max_requests:
                disposition = GapFillingDisposition.request_budget
                rationale = "request-count budget is exhausted"
            elif spent + candidate.evidence_cost > self.policy.evidence_cost_budget:
                disposition = GapFillingDisposition.evidence_budget
                rationale = "remaining evidence-cost budget cannot admit this gap"
            else:
                disposition = GapFillingDisposition.selected
                rationale = "gap has the highest remaining value within both budgets"
                request = self._request(candidate, priority=100 - len(requests))
                requests.append(request)
                spent += candidate.evidence_cost
            decisions.append(
                GapFillingDecision(
                    candidate_artifact_id=candidate.artifact_id,
                    source_artifact_id=candidate.source_artifact_id,
                    rank=rank,
                    expected_value=candidate.expected_value,
                    evidence_cost=candidate.evidence_cost,
                    disposition=disposition,
                    rationale=rationale,
                    request_artifact_id=(
                        None if request is None else request.artifact_id
                    ),
                )
            )
        stop_reasons = _stop_reasons(tuple(decisions))
        graph_id = ordered[0].graph_artifact_id if ordered else content_artifact_id(())
        payload = {
            "schema_version": "bijux.canon.reason.gap_filling_plan.v1",
            "graph_artifact_id": graph_id,
            "policy": self.policy.model_dump(mode="json"),
            "requests": tuple(item.model_dump(mode="json") for item in requests),
            "decisions": tuple(item.model_dump(mode="json") for item in decisions),
            "projected_evidence_cost": spent,
            "stop_reasons": tuple(item.value for item in stop_reasons),
        }
        return GapFillingPlan(
            artifact_id=content_artifact_id(payload),
            graph_artifact_id=graph_id,
            policy=self.policy,
            requests=tuple(requests),
            decisions=tuple(decisions),
            projected_evidence_cost=spent,
            stop_reasons=stop_reasons,
        )

    def fill(self, plan: GapFillingPlan, port: RetrievalEvidencePort) -> GapFillingRun:
        """Execute only admitted requests or close a no-retrieval stopping cycle."""

        if not plan.requests:
            return _run(plan, None, ())
        retrieval = GapRetrievalService(
            GapRetrievalPolicy(
                max_requests=plan.policy.max_requests,
                max_evidence_per_request=plan.policy.max_evidence_per_request,
                max_query_characters=plan.policy.max_query_characters,
            )
        ).retrieve(plan.requests, port)
        by_request = {
            item.request_artifact_id: item
            for item in plan.decisions
            if item.request_artifact_id is not None
        }
        records = tuple(
            _execution_record(item, by_request[item.request_artifact_id])
            for item in retrieval.records
        )
        return _run(plan, retrieval.artifact_id, records)

    def _request(
        self, candidate: GapFillingCandidate, *, priority: int
    ) -> ScopedRetrievalRequest:
        return create_gap_retrieval_request(
            graph_artifact_id=candidate.graph_artifact_id,
            target_artifact_id=candidate.source_artifact_id,
            target_kind=RetrievalTargetKind.claim_gap,
            scope_artifact_id=candidate.scope_artifact_id,
            query_text=candidate.query_text,
            rationale=candidate.rationale,
            evidence_needs=("evidence capable of resolving the ranked graph gap",),
            prior_evidence_artifact_ids=candidate.prior_evidence_artifact_ids,
            priority=priority,
            top_k=_plan_top_k(candidate, self.policy),
        )


def _plan_top_k(candidate: GapFillingCandidate, policy: GapFillingPolicy) -> int:

    return min(candidate.evidence_cost, policy.max_evidence_per_request)


def create_gap_filling_candidate(
    *,
    graph_artifact_id: str,
    source_artifact_id: str,
    source_kind: GapFillingSourceKind,
    target_claim_artifact_id: str | None,
    scope_artifact_id: str,
    query_text: str,
    rationale: str,
    answer_impact: float,
    resolution_probability: float,
    evidence_cost: int,
    status: GapResolutionStatus = GapResolutionStatus.unresolved,
    prior_evidence_artifact_ids: tuple[str, ...] = (),
) -> GapFillingCandidate:
    """Create one immutable expected-value candidate from a graph gap."""

    normalized_query = " ".join(query_text.split())
    normalized_rationale = " ".join(rationale.split())
    ordered_prior = tuple(sorted(prior_evidence_artifact_ids))
    payload = {
        "graph_artifact_id": graph_artifact_id,
        "source_artifact_id": source_artifact_id,
        "source_kind": source_kind.value,
        "target_claim_artifact_id": target_claim_artifact_id,
        "scope_artifact_id": scope_artifact_id,
        "query_text": normalized_query,
        "rationale": normalized_rationale,
        "answer_impact": answer_impact,
        "resolution_probability": resolution_probability,
        "evidence_cost": evidence_cost,
        "status": status.value,
        "prior_evidence_artifact_ids": ordered_prior,
    }
    return GapFillingCandidate(
        artifact_id=content_artifact_id(payload),
        graph_artifact_id=graph_artifact_id,
        source_artifact_id=source_artifact_id,
        source_kind=source_kind,
        target_claim_artifact_id=target_claim_artifact_id,
        scope_artifact_id=scope_artifact_id,
        query_text=normalized_query,
        rationale=normalized_rationale,
        answer_impact=answer_impact,
        resolution_probability=resolution_probability,
        evidence_cost=evidence_cost,
        status=status,
        prior_evidence_artifact_ids=ordered_prior,
    )


def create_deficiency_gap_candidate(
    deficiency: ResearchDeficiency,
    *,
    scope_artifact_id: str,
    query_text: str,
    resolution_probability: float,
    evidence_cost: int,
    prior_evidence_artifact_ids: tuple[str, ...] = (),
) -> GapFillingCandidate:
    """Convert a first-class research deficiency into a ranked fill candidate."""

    return create_gap_filling_candidate(
        graph_artifact_id=deficiency.graph_artifact_id,
        source_artifact_id=deficiency.artifact_id,
        source_kind=GapFillingSourceKind.research_deficiency,
        target_claim_artifact_id=deficiency.target_claim_artifact_id,
        scope_artifact_id=scope_artifact_id,
        query_text=query_text,
        rationale=deficiency.required_action,
        answer_impact=deficiency.priority / 100,
        resolution_probability=resolution_probability,
        evidence_cost=evidence_cost,
        status=(
            GapResolutionStatus.resolved
            if deficiency.status is ResearchDeficiencyStatus.resolved
            else GapResolutionStatus.unresolved
        ),
        prior_evidence_artifact_ids=prior_evidence_artifact_ids,
    )


def _stop_reasons(
    decisions: tuple[GapFillingDecision, ...],
) -> tuple[GapFillingStopReason, ...]:
    mapped = {
        GapFillingDisposition.expected_value_below_threshold: (
            GapFillingStopReason.expected_value_floor
        ),
        GapFillingDisposition.request_budget: GapFillingStopReason.request_budget,
        GapFillingDisposition.evidence_budget: GapFillingStopReason.evidence_budget,
        GapFillingDisposition.query_budget: GapFillingStopReason.query_budget,
    }
    reasons = {
        mapped[item.disposition] for item in decisions if item.disposition in mapped
    }
    if not reasons:
        reasons.add(GapFillingStopReason.candidates_exhausted)
    return tuple(sorted(reasons))


def _execution_record(
    record: GapRetrievalRecord, decision: GapFillingDecision
) -> GapFillingExecutionRecord:
    payload = {
        "candidate_artifact_id": decision.candidate_artifact_id,
        "source_artifact_id": decision.source_artifact_id,
        "request_artifact_id": record.request_artifact_id,
        "retrieval_record_artifact_id": record.artifact_id,
        "change": record.change.value,
        "added_evidence_artifact_ids": record.added_evidence_artifact_ids,
    }
    return GapFillingExecutionRecord(
        artifact_id=content_artifact_id(payload),
        candidate_artifact_id=decision.candidate_artifact_id,
        source_artifact_id=decision.source_artifact_id,
        request_artifact_id=record.request_artifact_id,
        retrieval_record_artifact_id=record.artifact_id,
        change=record.change,
        added_evidence_artifact_ids=record.added_evidence_artifact_ids,
    )


def _run(
    plan: GapFillingPlan,
    retrieval_run_artifact_id: str | None,
    records: tuple[GapFillingExecutionRecord, ...],
) -> GapFillingRun:
    payload = {
        "schema_version": "bijux.canon.reason.gap_filling_run.v1",
        "plan_artifact_id": plan.artifact_id,
        "retrieval_run_artifact_id": retrieval_run_artifact_id,
        "records": tuple(item.model_dump(mode="json") for item in records),
        "stop_reasons": tuple(item.value for item in plan.stop_reasons),
    }
    return GapFillingRun(
        artifact_id=content_artifact_id(payload),
        plan_artifact_id=plan.artifact_id,
        retrieval_run_artifact_id=retrieval_run_artifact_id,
        records=records,
        stop_reasons=plan.stop_reasons,
    )


__all__ = [
    "GapFillingCandidate",
    "GapFillingDecision",
    "GapFillingDisposition",
    "GapFillingError",
    "GapFillingErrorCode",
    "GapFillingExecutionRecord",
    "GapFillingPlan",
    "GapFillingPolicy",
    "GapFillingRun",
    "GapFillingService",
    "GapFillingSourceKind",
    "GapFillingStopReason",
    "GapResolutionStatus",
    "create_deficiency_gap_candidate",
    "create_gap_filling_candidate",
]
