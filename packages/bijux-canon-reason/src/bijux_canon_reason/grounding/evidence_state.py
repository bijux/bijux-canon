# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Evidence conditions governing whether a grounded answer may be emitted."""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.evidence_packets import PacketCompleteness
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)


class RetrievalEvidenceStatus(StrEnum):
    """Installed retrieval outcome presented to answer admission."""

    success = "success"
    insufficient = "insufficient"
    refused = "refused"
    failed = "failed"


class VexEvidenceStatus(StrEnum):
    """Dense witness disposition, including bounded exact recovery."""

    verified = "verified"
    exact_fallback_verified = "exact-fallback-verified"
    below_policy = "below-policy"
    failed = "failed"
    not_applicable = "not-applicable"


class GroundingEvidenceState(StableModel):
    """Content-bound upstream evidence state used by abstention policy."""

    schema_version: str = "bijux.canon.reason.grounding_evidence_state.v1"
    artifact_id: str
    retrieval_status: RetrievalEvidenceStatus
    vex_status: VexEvidenceStatus
    retrieved_evidence_count: int
    selected_evidence_count: int
    packet_completeness: PacketCompleteness
    unsafe_or_unverified: bool = False
    budget_exhausted: bool = False
    policy_detail: str | None = None
    remediation: str | None = None

    @classmethod
    def create(
        cls,
        *,
        retrieval_status: RetrievalEvidenceStatus,
        vex_status: VexEvidenceStatus,
        retrieved_evidence_count: int,
        selected_evidence_count: int,
        packet_completeness: PacketCompleteness,
        unsafe_or_unverified: bool = False,
        budget_exhausted: bool = False,
        policy_detail: str | None = None,
        remediation: str | None = None,
    ) -> Self:
        payload = {
            "schema_version": "bijux.canon.reason.grounding_evidence_state.v1",
            "retrieval_status": retrieval_status.value,
            "vex_status": vex_status.value,
            "retrieved_evidence_count": retrieved_evidence_count,
            "selected_evidence_count": selected_evidence_count,
            "packet_completeness": packet_completeness.value,
            "unsafe_or_unverified": unsafe_or_unverified,
            "budget_exhausted": budget_exhausted,
            "policy_detail": policy_detail,
            "remediation": remediation,
        }
        return cls.model_validate(
            {"artifact_id": content_artifact_id(payload), **payload}
        )

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_state(self) -> Self:
        if self.retrieved_evidence_count < 0 or self.selected_evidence_count < 0:
            raise ValueError("evidence counts cannot be negative")
        if self.selected_evidence_count > self.retrieved_evidence_count:
            raise ValueError("selected evidence exceeds retrieved evidence")
        if self.retrieval_status is RetrievalEvidenceStatus.success and not (
            self.retrieved_evidence_count and self.selected_evidence_count
        ):
            raise ValueError("successful retrieval requires selected evidence")
        if self.retrieval_status in {
            RetrievalEvidenceStatus.refused,
            RetrievalEvidenceStatus.failed,
        } and self.selected_evidence_count:
            raise ValueError("unusable retrieval cannot expose selected evidence")
        if self.vex_status in {VexEvidenceStatus.below_policy, VexEvidenceStatus.failed}:
            if self.retrieval_status is RetrievalEvidenceStatus.success:
                raise ValueError("unresolved VEX failure cannot be called successful")
        if (self.policy_detail is None) != (self.remediation is None):
            raise ValueError("evidence policy detail and remediation must be paired")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("grounding evidence state identity does not match")
        return self


__all__ = [
    "GroundingEvidenceState",
    "RetrievalEvidenceStatus",
    "VexEvidenceStatus",
]
