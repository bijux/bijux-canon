# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Plan and record bounded skeptical searches for important research claims."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
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


class CounterevidenceOmissionReason(StrEnum):
    """Why a claim did not receive a skeptical query in this cycle."""

    below_importance = "below_importance"
    claim_budget = "claim_budget"


class CounterevidenceSearchOutcome(StrEnum):
    """Honest interpretation of one skeptical retrieval result."""

    candidate_evidence_found = "candidate_evidence_found"
    no_new_counterevidence_found = "no_new_counterevidence_found"
    retrieval_refused = "retrieval_refused"


class CounterevidenceErrorCode(StrEnum):
    """Stable failures raised before skeptical search execution."""

    duplicate_claim = "duplicate_claim"
    mixed_graph_identity = "mixed_graph_identity"
    query_budget_exceeded = "query_budget_exceeded"
    plan_has_no_searches = "plan_has_no_searches"


class CounterevidenceError(ValueError):
    """A counterevidence search cannot preserve its declared bounds."""

    def __init__(self, code: CounterevidenceErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class CounterevidencePolicy(StableModel):
    """Hard importance, claim, query, and result limits for one cycle."""

    minimum_claim_importance: int = 60
    max_claims: int = 8
    max_query_characters: int = 2_048
    top_k: int = 10

    @model_validator(mode="after")
    def _validate_bounds(self) -> Self:
        if not 1 <= self.minimum_claim_importance <= 100:
            raise ValueError("minimum claim importance must be within 1..100")
        if not 1 <= self.max_claims <= 64:
            raise ValueError("counterevidence claim budget must be within 1..64")
        if not 64 <= self.max_query_characters <= 100_000:
            raise ValueError("counterevidence query bound must be within 64..100000")
        if not 1 <= self.top_k <= 1_000:
            raise ValueError("counterevidence top_k must be within 1..1000")
        return self


class CounterevidenceTarget(StableModel):
    """One atomic claim eligible for deliberate skeptical search."""

    artifact_id: str
    graph_artifact_id: str
    claim_artifact_id: str
    scope_artifact_id: str
    statement: str
    importance: int
    known_evidence_artifact_ids: tuple[str, ...]

    @field_validator(
        "artifact_id", "graph_artifact_id", "claim_artifact_id", "scope_artifact_id"
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("statement")
    @classmethod
    def _validate_statement(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("counterevidence targets require a claim statement")
        return normalized

    @field_validator("known_evidence_artifact_ids")
    @classmethod
    def _validate_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("known evidence identities must be unique")
        return tuple(sorted(require_artifact_id(item) for item in value))

    @model_validator(mode="after")
    def _validate_target(self) -> Self:
        if not 1 <= self.importance <= 100:
            raise ValueError("claim importance must be within 1..100")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("counterevidence target identity does not match")
        return self


class CounterevidenceOmission(StableModel):
    """Explicitly retained reason that a target was not searched."""

    target_artifact_id: str
    claim_artifact_id: str
    importance: int
    reason: CounterevidenceOmissionReason

    @field_validator("target_artifact_id", "claim_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)


class CounterevidencePlan(StableModel):
    """Content-addressed skeptical queries and all bounded omissions."""

    schema_version: Literal["bijux.canon.reason.counterevidence_plan.v1"] = (
        "bijux.canon.reason.counterevidence_plan.v1"
    )
    artifact_id: str
    graph_artifact_id: str
    policy: CounterevidencePolicy
    requests: tuple[ScopedRetrievalRequest, ...]
    omissions: tuple[CounterevidenceOmission, ...]

    @field_validator("artifact_id", "graph_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_plan(self) -> Self:
        if len(self.requests) > self.policy.max_claims:
            raise ValueError("counterevidence plan exceeds its claim budget")
        request_claims = tuple(item.target_artifact_id for item in self.requests)
        omitted_claims = tuple(item.claim_artifact_id for item in self.omissions)
        if len(request_claims) != len(set(request_claims)):
            raise ValueError("counterevidence requests must target unique claims")
        if set(request_claims) & set(omitted_claims):
            raise ValueError("a claim cannot be both searched and omitted")
        if any(
            item.graph_artifact_id != self.graph_artifact_id
            or item.target_kind is not RetrievalTargetKind.claim_gap
            for item in self.requests
        ):
            raise ValueError(
                "counterevidence queries require one graph and claim targets"
            )
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("counterevidence plan identity does not match")
        return self


class CounterevidenceSearchRecord(StableModel):
    """Interpretation of one search without treating absence as confirmation."""

    artifact_id: str
    claim_artifact_id: str
    request_artifact_id: str
    retrieval_record_artifact_id: str
    outcome: CounterevidenceSearchOutcome
    candidate_evidence_artifact_ids: tuple[str, ...]
    negative_search_statement: str | None
    requires_relation_classification: bool

    @field_validator(
        "artifact_id",
        "claim_artifact_id",
        "request_artifact_id",
        "retrieval_record_artifact_id",
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("candidate_evidence_artifact_ids")
    @classmethod
    def _validate_candidates(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("counterevidence candidate identities must be unique")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_record(self) -> Self:
        if self.outcome is CounterevidenceSearchOutcome.candidate_evidence_found:
            if (
                not self.candidate_evidence_artifact_ids
                or self.negative_search_statement is not None
                or not self.requires_relation_classification
            ):
                raise ValueError(
                    "candidate evidence must remain pending classification"
                )
        elif self.candidate_evidence_artifact_ids:
            raise ValueError("negative or refused searches cannot expose candidates")
        elif self.outcome is CounterevidenceSearchOutcome.no_new_counterevidence_found:
            if (
                not self.negative_search_statement
                or self.requires_relation_classification
            ):
                raise ValueError(
                    "negative searches require an honest bounded statement"
                )
        elif self.negative_search_statement is not None:
            raise ValueError("refused searches are not negative search results")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("counterevidence search record identity does not match")
        return self


class CounterevidenceSearchRun(StableModel):
    """Closed skeptical-search cycle and explicit stopping guard."""

    schema_version: Literal["bijux.canon.reason.counterevidence_search_run.v1"] = (
        "bijux.canon.reason.counterevidence_search_run.v1"
    )
    artifact_id: str
    plan_artifact_id: str
    retrieval_run_artifact_id: str
    records: tuple[CounterevidenceSearchRecord, ...]
    unsearched_important_claim_artifact_ids: tuple[str, ...]
    confirmation_only_stop_blocked: bool

    @field_validator("artifact_id", "plan_artifact_id", "retrieval_run_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("unsearched_important_claim_artifact_ids")
    @classmethod
    def _validate_unsearched(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("unsearched important claims must be unique")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_run(self) -> Self:
        incomplete = bool(self.unsearched_important_claim_artifact_ids) or any(
            item.outcome
            in {
                CounterevidenceSearchOutcome.candidate_evidence_found,
                CounterevidenceSearchOutcome.retrieval_refused,
            }
            for item in self.records
        )
        if self.confirmation_only_stop_blocked != incomplete:
            raise ValueError(
                "counterevidence stopping guard does not match search state"
            )
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("counterevidence search run identity does not match")
        return self


class CounterevidenceSearchService:
    """Generate skeptical claim queries and execute them through the retrieval port."""

    def __init__(self, policy: CounterevidencePolicy | None = None) -> None:
        self.policy = policy or CounterevidencePolicy()

    def plan(self, targets: tuple[CounterevidenceTarget, ...]) -> CounterevidencePlan:
        """Select important claims deterministically and retain every omission."""

        claim_ids = tuple(item.claim_artifact_id for item in targets)
        if len(claim_ids) != len(set(claim_ids)):
            raise CounterevidenceError(
                CounterevidenceErrorCode.duplicate_claim,
                "counterevidence targets must refer to unique claims",
            )
        graph_ids = {item.graph_artifact_id for item in targets}
        if len(graph_ids) > 1:
            raise CounterevidenceError(
                CounterevidenceErrorCode.mixed_graph_identity,
                "counterevidence targets cannot mix graph revisions",
            )
        ordered = tuple(
            sorted(targets, key=lambda item: (-item.importance, item.artifact_id))
        )
        eligible = tuple(
            item
            for item in ordered
            if item.importance >= self.policy.minimum_claim_importance
        )
        selected = eligible[: self.policy.max_claims]
        requests = tuple(self._request(item) for item in selected)
        omissions = tuple(
            CounterevidenceOmission(
                target_artifact_id=item.artifact_id,
                claim_artifact_id=item.claim_artifact_id,
                importance=item.importance,
                reason=(
                    CounterevidenceOmissionReason.below_importance
                    if item.importance < self.policy.minimum_claim_importance
                    else CounterevidenceOmissionReason.claim_budget
                ),
            )
            for item in ordered
            if item not in selected
        )
        graph_id = ordered[0].graph_artifact_id if ordered else content_artifact_id(())
        payload = {
            "schema_version": "bijux.canon.reason.counterevidence_plan.v1",
            "graph_artifact_id": graph_id,
            "policy": self.policy.model_dump(mode="json"),
            "requests": tuple(item.model_dump(mode="json") for item in requests),
            "omissions": tuple(item.model_dump(mode="json") for item in omissions),
        }
        return CounterevidencePlan(
            artifact_id=content_artifact_id(payload),
            graph_artifact_id=graph_id,
            policy=self.policy,
            requests=requests,
            omissions=omissions,
        )

    def search(
        self, plan: CounterevidencePlan, port: RetrievalEvidencePort
    ) -> CounterevidenceSearchRun:
        """Execute a non-empty plan and preserve negative searches without inference."""

        if not plan.requests:
            raise CounterevidenceError(
                CounterevidenceErrorCode.plan_has_no_searches,
                "counterevidence execution requires at least one admitted query",
            )
        retrieval = GapRetrievalService(
            GapRetrievalPolicy(
                max_requests=plan.policy.max_claims,
                max_evidence_per_request=plan.policy.top_k,
                max_query_characters=plan.policy.max_query_characters,
            )
        ).retrieve(plan.requests, port)
        records = tuple(_search_record(item) for item in retrieval.records)
        unsearched = tuple(
            item.claim_artifact_id
            for item in plan.omissions
            if item.reason is CounterevidenceOmissionReason.claim_budget
        )
        blocked = bool(unsearched) or any(
            item.outcome
            in {
                CounterevidenceSearchOutcome.candidate_evidence_found,
                CounterevidenceSearchOutcome.retrieval_refused,
            }
            for item in records
        )
        payload = {
            "schema_version": "bijux.canon.reason.counterevidence_search_run.v1",
            "plan_artifact_id": plan.artifact_id,
            "retrieval_run_artifact_id": retrieval.artifact_id,
            "records": tuple(item.model_dump(mode="json") for item in records),
            "unsearched_important_claim_artifact_ids": unsearched,
            "confirmation_only_stop_blocked": blocked,
        }
        return CounterevidenceSearchRun(
            artifact_id=content_artifact_id(payload),
            plan_artifact_id=plan.artifact_id,
            retrieval_run_artifact_id=retrieval.artifact_id,
            records=records,
            unsearched_important_claim_artifact_ids=unsearched,
            confirmation_only_stop_blocked=blocked,
        )

    def _request(self, target: CounterevidenceTarget) -> ScopedRetrievalRequest:
        query = (
            f"{target.statement} contradictory evidence failed replication "
            "null result limitation boundary condition"
        )
        if len(query) > self.policy.max_query_characters:
            raise CounterevidenceError(
                CounterevidenceErrorCode.query_budget_exceeded,
                "skeptical query exceeds the configured character budget",
            )
        return create_gap_retrieval_request(
            graph_artifact_id=target.graph_artifact_id,
            target_artifact_id=target.claim_artifact_id,
            target_kind=RetrievalTargetKind.claim_gap,
            scope_artifact_id=target.scope_artifact_id,
            query_text=query,
            rationale=(
                "Deliberately test an important claim against disagreement, null "
                "results, replication failure, and scope limitations."
            ),
            evidence_needs=(
                "evidence that directly opposes the claim",
                "failed replication or null result",
                "scope or boundary conditions that weaken generalization",
            ),
            prior_evidence_artifact_ids=target.known_evidence_artifact_ids,
            priority=target.importance,
            top_k=self.policy.top_k,
        )


def create_counterevidence_target(
    *,
    graph_artifact_id: str,
    claim_artifact_id: str,
    scope_artifact_id: str,
    statement: str,
    importance: int,
    known_evidence_artifact_ids: tuple[str, ...] = (),
) -> CounterevidenceTarget:
    """Create one immutable claim target for skeptical search."""

    normalized = " ".join(statement.split())
    ordered_evidence = tuple(sorted(known_evidence_artifact_ids))
    payload = {
        "graph_artifact_id": graph_artifact_id,
        "claim_artifact_id": claim_artifact_id,
        "scope_artifact_id": scope_artifact_id,
        "statement": normalized,
        "importance": importance,
        "known_evidence_artifact_ids": ordered_evidence,
    }
    return CounterevidenceTarget(
        artifact_id=content_artifact_id(payload),
        graph_artifact_id=graph_artifact_id,
        claim_artifact_id=claim_artifact_id,
        scope_artifact_id=scope_artifact_id,
        statement=normalized,
        importance=importance,
        known_evidence_artifact_ids=ordered_evidence,
    )


def _search_record(record: GapRetrievalRecord) -> CounterevidenceSearchRecord:
    if record.change is EvidenceChange.evidence_added:
        outcome = CounterevidenceSearchOutcome.candidate_evidence_found
        candidates = record.added_evidence_artifact_ids
        negative_statement = None
        requires_classification = True
    elif record.change is EvidenceChange.no_new_evidence:
        outcome = CounterevidenceSearchOutcome.no_new_counterevidence_found
        candidates = ()
        negative_statement = (
            "No new counterevidence was found within this request's exact scope and "
            "limits; absence is not support for the claim."
        )
        requires_classification = False
    else:
        outcome = CounterevidenceSearchOutcome.retrieval_refused
        candidates = ()
        negative_statement = None
        requires_classification = False
    payload = {
        "claim_artifact_id": record.target_artifact_id,
        "request_artifact_id": record.request_artifact_id,
        "retrieval_record_artifact_id": record.artifact_id,
        "outcome": outcome.value,
        "candidate_evidence_artifact_ids": candidates,
        "negative_search_statement": negative_statement,
        "requires_relation_classification": requires_classification,
    }
    return CounterevidenceSearchRecord(
        artifact_id=content_artifact_id(payload),
        claim_artifact_id=record.target_artifact_id,
        request_artifact_id=record.request_artifact_id,
        retrieval_record_artifact_id=record.artifact_id,
        outcome=outcome,
        candidate_evidence_artifact_ids=candidates,
        negative_search_statement=negative_statement,
        requires_relation_classification=requires_classification,
    )


__all__ = [
    "CounterevidenceError",
    "CounterevidenceErrorCode",
    "CounterevidenceOmission",
    "CounterevidenceOmissionReason",
    "CounterevidencePlan",
    "CounterevidencePolicy",
    "CounterevidenceSearchOutcome",
    "CounterevidenceSearchRecord",
    "CounterevidenceSearchRun",
    "CounterevidenceSearchService",
    "CounterevidenceTarget",
    "create_counterevidence_target",
]
