# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Issue scoped retrieval requests for unresolved research graph targets."""

from __future__ import annotations

from enum import StrEnum
import hashlib
from typing import Literal, Protocol, Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
    require_sha256,
)
from bijux_canon_reason.research.question_decomposition import (
    ResearchSubquestion,
    SubquestionStatus,
)


class RetrievalTargetKind(StrEnum):
    """Research graph node that caused a retrieval request."""

    subquestion = "subquestion"
    claim_gap = "claim_gap"


class RetrievalBatchStatus(StrEnum):
    """Typed outcome returned by an index-owned retrieval adapter."""

    success = "success"
    no_matches = "no_matches"
    refused = "refused"


class EvidenceChange(StrEnum):
    """How one retrieval batch changed known evidence."""

    evidence_added = "evidence_added"
    no_new_evidence = "no_new_evidence"
    retrieval_refused = "retrieval_refused"


class GapRetrievalErrorCode(StrEnum):
    """Stable fail-closed retrieval orchestration errors."""

    request_budget_exceeded = "request_budget_exceeded"
    duplicate_request_identity = "duplicate_request_identity"
    duplicate_target = "duplicate_target"
    mixed_graph_identity = "mixed_graph_identity"
    target_resolved = "target_resolved"
    request_identity_mismatch = "request_identity_mismatch"
    query_identity_mismatch = "query_identity_mismatch"
    scope_identity_mismatch = "scope_identity_mismatch"
    result_limit_exceeded = "result_limit_exceeded"


class GapRetrievalError(ValueError):
    """A retrieval request or adapter result violates graph boundaries."""

    def __init__(self, code: GapRetrievalErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class GapRetrievalPolicy(StableModel):
    """Hard per-cycle request and evidence limits."""

    max_requests: int = 16
    max_evidence_per_request: int = 20
    max_query_characters: int = 4_096

    @model_validator(mode="after")
    def _validate_bounds(self) -> Self:
        if not 1 <= self.max_requests <= 128:
            raise ValueError("retrieval request budget must be within 1..128")
        if not 1 <= self.max_evidence_per_request <= 1_000:
            raise ValueError("per-request evidence budget must be within 1..1000")
        if not 1 <= self.max_query_characters <= 100_000:
            raise ValueError("retrieval query bound must be within 1..100000")
        return self


class ScopedRetrievalRequest(StableModel):
    """Content-addressed reason-owned request to the index retrieval port."""

    schema_version: Literal["bijux.canon.reason.scoped_retrieval_request.v1"] = (
        "bijux.canon.reason.scoped_retrieval_request.v1"
    )
    artifact_id: str
    graph_artifact_id: str
    target_artifact_id: str
    target_kind: RetrievalTargetKind
    scope_artifact_id: str
    query_text: str
    query_text_sha256: str
    rationale: str
    evidence_needs: tuple[str, ...]
    prior_evidence_artifact_ids: tuple[str, ...]
    priority: int
    top_k: int

    @field_validator(
        "artifact_id",
        "graph_artifact_id",
        "target_artifact_id",
        "scope_artifact_id",
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("query_text_sha256")
    @classmethod
    def _validate_sha256(cls, value: str) -> str:
        return require_sha256(value)

    @field_validator("query_text", "rationale")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("retrieval query and rationale must not be empty")
        return normalized

    @field_validator("evidence_needs")
    @classmethod
    def _validate_evidence_needs(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or any(not item.strip() for item in value):
            raise ValueError("retrieval requests require evidence needs")
        if len(value) != len(set(value)):
            raise ValueError("retrieval evidence needs must be unique")
        return value

    @field_validator("prior_evidence_artifact_ids")
    @classmethod
    def _validate_prior_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("prior evidence identities must be unique")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_request(self) -> Self:
        if hashlib.sha256(self.query_text.encode()).hexdigest() != (
            self.query_text_sha256
        ):
            raise ValueError("retrieval query hash does not match")
        if not 1 <= self.priority <= 100:
            raise ValueError("retrieval priority must be within 1..100")
        if not 1 <= self.top_k <= 1_000:
            raise ValueError("retrieval top_k must be within 1..1000")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("retrieval request identity does not match its payload")
        return self


class RetrievalEvidenceBatch(StableModel):
    """Minimal index-owned result normalized at the reason boundary."""

    schema_version: Literal["bijux.canon.reason.retrieval_evidence_batch.v1"] = (
        "bijux.canon.reason.retrieval_evidence_batch.v1"
    )
    artifact_id: str
    request_artifact_id: str
    retrieval_trace_artifact_id: str
    generation_artifact_id: str
    query_text_sha256: str
    scope_artifact_id: str
    status: RetrievalBatchStatus
    evidence_artifact_ids: tuple[str, ...]
    refusal_code: str | None

    @field_validator(
        "artifact_id",
        "request_artifact_id",
        "retrieval_trace_artifact_id",
        "generation_artifact_id",
        "scope_artifact_id",
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("query_text_sha256")
    @classmethod
    def _validate_sha256(cls, value: str) -> str:
        return require_sha256(value)

    @field_validator("evidence_artifact_ids")
    @classmethod
    def _validate_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("retrieval evidence identities must be unique")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_batch(self) -> Self:
        if self.status is RetrievalBatchStatus.success:
            if not self.evidence_artifact_ids or self.refusal_code is not None:
                raise ValueError(
                    "successful retrieval requires evidence without refusal"
                )
        elif self.evidence_artifact_ids:
            raise ValueError("non-successful retrieval cannot expose evidence")
        elif self.status is RetrievalBatchStatus.refused:
            if self.refusal_code is None or not self.refusal_code.strip():
                raise ValueError("refused retrieval requires a refusal code")
        elif self.refusal_code is not None:
            raise ValueError("no-match retrieval cannot expose a refusal code")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("retrieval batch identity does not match its payload")
        return self


class GapRetrievalRecord(StableModel):
    """Auditable evidence delta caused by one scoped request."""

    artifact_id: str
    request_artifact_id: str
    retrieval_batch_artifact_id: str
    retrieval_trace_artifact_id: str
    target_artifact_id: str
    prior_evidence_artifact_ids: tuple[str, ...]
    added_evidence_artifact_ids: tuple[str, ...]
    repeated_evidence_artifact_ids: tuple[str, ...]
    change: EvidenceChange
    rationale: str

    @field_validator(
        "artifact_id",
        "request_artifact_id",
        "retrieval_batch_artifact_id",
        "retrieval_trace_artifact_id",
        "target_artifact_id",
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_record(self) -> Self:
        groups = (
            self.prior_evidence_artifact_ids,
            self.added_evidence_artifact_ids,
            self.repeated_evidence_artifact_ids,
        )
        for group in groups:
            if len(group) != len(set(group)):
                raise ValueError("retrieval evidence delta identities must be unique")
            for item in group:
                require_artifact_id(item)
        if set(self.added_evidence_artifact_ids) & set(
            self.repeated_evidence_artifact_ids
        ):
            raise ValueError("added and repeated evidence must be disjoint")
        if self.change is EvidenceChange.evidence_added:
            if not self.added_evidence_artifact_ids:
                raise ValueError("evidence_added requires new evidence")
        elif self.added_evidence_artifact_ids:
            raise ValueError("non-additive retrieval cannot expose added evidence")
        if not self.rationale:
            raise ValueError("retrieval records require a change rationale")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("gap retrieval record identity does not match")
        return self


class GapRetrievalRun(StableModel):
    """Content-addressed ordered retrieval cycle for one graph revision."""

    schema_version: Literal["bijux.canon.reason.gap_retrieval_run.v1"] = (
        "bijux.canon.reason.gap_retrieval_run.v1"
    )
    artifact_id: str
    graph_artifact_id: str
    policy: GapRetrievalPolicy
    request_artifact_ids: tuple[str, ...]
    records: tuple[GapRetrievalRecord, ...]

    @field_validator("artifact_id", "graph_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_run(self) -> Self:
        if self.request_artifact_ids != tuple(
            item.request_artifact_id for item in self.records
        ):
            raise ValueError("retrieval run must close every request in order")
        if len(self.records) > self.policy.max_requests:
            raise ValueError("retrieval run exceeds its request budget")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("gap retrieval run identity does not match")
        return self


class RetrievalEvidencePort(Protocol):
    """Index-owned retrieval boundary consumed by reason."""

    def retrieve(self, request: ScopedRetrievalRequest) -> RetrievalEvidenceBatch:
        """Execute one immutable scoped request and return exact evidence IDs."""


class GapRetrievalService:
    """Execute unresolved graph requests and preserve their exact evidence delta."""

    def __init__(self, policy: GapRetrievalPolicy | None = None) -> None:
        self.policy = policy or GapRetrievalPolicy()

    def retrieve(
        self,
        requests: tuple[ScopedRetrievalRequest, ...],
        port: RetrievalEvidencePort,
    ) -> GapRetrievalRun:
        """Execute every admitted request once in deterministic priority order."""

        if not requests:
            raise ValueError("gap retrieval requires at least one request")
        if len(requests) > self.policy.max_requests:
            raise GapRetrievalError(
                GapRetrievalErrorCode.request_budget_exceeded,
                "retrieval requests exceed the configured cycle budget",
            )
        request_ids = tuple(item.artifact_id for item in requests)
        if len(request_ids) != len(set(request_ids)):
            raise GapRetrievalError(
                GapRetrievalErrorCode.duplicate_request_identity,
                "retrieval request identities must be unique",
            )
        targets = tuple(item.target_artifact_id for item in requests)
        if len(targets) != len(set(targets)):
            raise GapRetrievalError(
                GapRetrievalErrorCode.duplicate_target,
                "one retrieval cycle may issue only one request per graph target",
            )
        graph_ids = {item.graph_artifact_id for item in requests}
        if len(graph_ids) != 1:
            raise GapRetrievalError(
                GapRetrievalErrorCode.mixed_graph_identity,
                "one retrieval cycle cannot mix graph revisions",
            )
        ordered = tuple(
            sorted(requests, key=lambda item: (-item.priority, item.artifact_id))
        )
        records = tuple(self._execute(request, port) for request in ordered)
        graph_artifact_id = ordered[0].graph_artifact_id
        payload = {
            "schema_version": "bijux.canon.reason.gap_retrieval_run.v1",
            "graph_artifact_id": graph_artifact_id,
            "policy": self.policy.model_dump(mode="json"),
            "request_artifact_ids": tuple(item.artifact_id for item in ordered),
            "records": tuple(item.model_dump(mode="json") for item in records),
        }
        return GapRetrievalRun(
            artifact_id=content_artifact_id(payload),
            graph_artifact_id=graph_artifact_id,
            policy=self.policy,
            request_artifact_ids=tuple(item.artifact_id for item in ordered),
            records=records,
        )

    def _execute(
        self,
        request: ScopedRetrievalRequest,
        port: RetrievalEvidencePort,
    ) -> GapRetrievalRecord:
        if len(request.query_text) > self.policy.max_query_characters:
            raise GapRetrievalError(
                GapRetrievalErrorCode.request_budget_exceeded,
                "retrieval query exceeds the configured character budget",
            )
        batch = port.retrieve(request)
        if batch.request_artifact_id != request.artifact_id:
            raise GapRetrievalError(
                GapRetrievalErrorCode.request_identity_mismatch,
                "retrieval batch refers to another request",
            )
        if batch.query_text_sha256 != request.query_text_sha256:
            raise GapRetrievalError(
                GapRetrievalErrorCode.query_identity_mismatch,
                "retrieval batch query identity differs from its request",
            )
        if batch.scope_artifact_id != request.scope_artifact_id:
            raise GapRetrievalError(
                GapRetrievalErrorCode.scope_identity_mismatch,
                "retrieval batch scope differs from its request",
            )
        if len(batch.evidence_artifact_ids) > min(
            request.top_k, self.policy.max_evidence_per_request
        ):
            raise GapRetrievalError(
                GapRetrievalErrorCode.result_limit_exceeded,
                "retrieval batch exceeds the admitted result limit",
            )
        prior = set(request.prior_evidence_artifact_ids)
        added = tuple(item for item in batch.evidence_artifact_ids if item not in prior)
        repeated = tuple(item for item in batch.evidence_artifact_ids if item in prior)
        if batch.status is RetrievalBatchStatus.refused:
            change = EvidenceChange.retrieval_refused
            rationale = f"retrieval refused with code {batch.refusal_code}"
        elif added:
            change = EvidenceChange.evidence_added
            rationale = (
                f"added {len(added)} evidence artifact(s); retained "
                f"{len(repeated)} previously known artifact(s)"
            )
        else:
            change = EvidenceChange.no_new_evidence
            rationale = (
                "retrieval returned no matches"
                if batch.status is RetrievalBatchStatus.no_matches
                else "retrieval returned only previously known evidence"
            )
        payload = {
            "request_artifact_id": request.artifact_id,
            "retrieval_batch_artifact_id": batch.artifact_id,
            "retrieval_trace_artifact_id": batch.retrieval_trace_artifact_id,
            "target_artifact_id": request.target_artifact_id,
            "prior_evidence_artifact_ids": request.prior_evidence_artifact_ids,
            "added_evidence_artifact_ids": added,
            "repeated_evidence_artifact_ids": repeated,
            "change": change.value,
            "rationale": rationale,
        }
        return GapRetrievalRecord(
            artifact_id=content_artifact_id(payload),
            request_artifact_id=request.artifact_id,
            retrieval_batch_artifact_id=batch.artifact_id,
            retrieval_trace_artifact_id=batch.retrieval_trace_artifact_id,
            target_artifact_id=request.target_artifact_id,
            prior_evidence_artifact_ids=request.prior_evidence_artifact_ids,
            added_evidence_artifact_ids=added,
            repeated_evidence_artifact_ids=repeated,
            change=change,
            rationale=rationale,
        )


def create_subquestion_retrieval_request(
    subquestion: ResearchSubquestion,
    *,
    graph_artifact_id: str,
    prior_evidence_artifact_ids: tuple[str, ...] = (),
    top_k: int = 10,
) -> ScopedRetrievalRequest:
    """Create a traceable request only for an unresolved subquestion."""

    if subquestion.status is SubquestionStatus.answered:
        raise GapRetrievalError(
            GapRetrievalErrorCode.target_resolved,
            "answered subquestions cannot issue unresolved retrieval requests",
        )
    return create_gap_retrieval_request(
        graph_artifact_id=graph_artifact_id,
        target_artifact_id=subquestion.artifact_id,
        target_kind=RetrievalTargetKind.subquestion,
        scope_artifact_id=subquestion.scope_artifact_id,
        query_text=subquestion.text,
        rationale=subquestion.rationale,
        evidence_needs=subquestion.evidence_needs,
        prior_evidence_artifact_ids=prior_evidence_artifact_ids,
        priority=subquestion.priority,
        top_k=top_k,
    )


def create_gap_retrieval_request(
    *,
    graph_artifact_id: str,
    target_artifact_id: str,
    target_kind: RetrievalTargetKind,
    scope_artifact_id: str,
    query_text: str,
    rationale: str,
    evidence_needs: tuple[str, ...],
    prior_evidence_artifact_ids: tuple[str, ...] = (),
    priority: int,
    top_k: int = 10,
) -> ScopedRetrievalRequest:
    """Create one content-addressed query for a subquestion or claim gap."""

    normalized_query = " ".join(query_text.split())
    query_hash = hashlib.sha256(normalized_query.encode()).hexdigest()
    payload = {
        "schema_version": "bijux.canon.reason.scoped_retrieval_request.v1",
        "graph_artifact_id": graph_artifact_id,
        "target_artifact_id": target_artifact_id,
        "target_kind": target_kind.value,
        "scope_artifact_id": scope_artifact_id,
        "query_text": normalized_query,
        "query_text_sha256": query_hash,
        "rationale": " ".join(rationale.split()),
        "evidence_needs": evidence_needs,
        "prior_evidence_artifact_ids": prior_evidence_artifact_ids,
        "priority": priority,
        "top_k": top_k,
    }
    return ScopedRetrievalRequest(
        artifact_id=content_artifact_id(payload),
        graph_artifact_id=graph_artifact_id,
        target_artifact_id=target_artifact_id,
        target_kind=target_kind,
        scope_artifact_id=scope_artifact_id,
        query_text=normalized_query,
        query_text_sha256=query_hash,
        rationale=" ".join(rationale.split()),
        evidence_needs=evidence_needs,
        prior_evidence_artifact_ids=prior_evidence_artifact_ids,
        priority=priority,
        top_k=top_k,
    )


def create_retrieval_evidence_batch(
    request: ScopedRetrievalRequest,
    *,
    retrieval_trace_artifact_id: str,
    generation_artifact_id: str,
    status: RetrievalBatchStatus,
    evidence_artifact_ids: tuple[str, ...],
    refusal_code: str | None = None,
) -> RetrievalEvidenceBatch:
    """Normalize an index adapter result with stable content identity."""

    payload = {
        "schema_version": "bijux.canon.reason.retrieval_evidence_batch.v1",
        "request_artifact_id": request.artifact_id,
        "retrieval_trace_artifact_id": retrieval_trace_artifact_id,
        "generation_artifact_id": generation_artifact_id,
        "query_text_sha256": request.query_text_sha256,
        "scope_artifact_id": request.scope_artifact_id,
        "status": status.value,
        "evidence_artifact_ids": evidence_artifact_ids,
        "refusal_code": refusal_code,
    }
    return RetrievalEvidenceBatch(
        artifact_id=content_artifact_id(payload),
        request_artifact_id=request.artifact_id,
        retrieval_trace_artifact_id=retrieval_trace_artifact_id,
        generation_artifact_id=generation_artifact_id,
        query_text_sha256=request.query_text_sha256,
        scope_artifact_id=request.scope_artifact_id,
        status=status,
        evidence_artifact_ids=evidence_artifact_ids,
        refusal_code=refusal_code,
    )


__all__ = [
    "EvidenceChange",
    "GapRetrievalError",
    "GapRetrievalErrorCode",
    "GapRetrievalPolicy",
    "GapRetrievalRecord",
    "GapRetrievalRun",
    "GapRetrievalService",
    "RetrievalBatchStatus",
    "RetrievalEvidenceBatch",
    "RetrievalEvidencePort",
    "RetrievalTargetKind",
    "ScopedRetrievalRequest",
    "create_gap_retrieval_request",
    "create_retrieval_evidence_batch",
    "create_subquestion_retrieval_request",
]
