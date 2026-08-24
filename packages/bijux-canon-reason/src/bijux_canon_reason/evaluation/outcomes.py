# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""System-output records kept structurally separate from evaluation truth."""

from __future__ import annotations

from enum import StrEnum
import hashlib
from typing import Literal

from pydantic import Field, field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.evaluation.truth import Identifier, NonEmptyText, Sha256


class SystemAnswerDisposition(StrEnum):
    """Top-level behavior of a system answer."""

    answered = "answered"
    partially_abstained = "partially_abstained"
    abstained = "abstained"
    failed = "failed"


class SystemClaimDisposition(StrEnum):
    """Behavior expressed for one emitted system claim."""

    asserted = "asserted"
    qualified = "qualified"
    abstained = "abstained"


class SystemCitation(StableModel):
    """Exact citation emitted by the evaluated system."""

    schema_version: Literal[
        "bijux.canon.evaluation.system-citation.v1",
        "bijux.canon.evaluation.system-citation.v2",
    ] = (
        "bijux.canon.evaluation.system-citation.v1"
    )
    citation_id: Identifier
    source_id: Identifier
    source_uri: NonEmptyText
    source_sha256: Sha256
    locator_id: Identifier
    exact_text_sha256: Sha256
    character_start: int = Field(ge=0)
    character_end: int = Field(gt=0)
    exact_text: str | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    chunk_id: str | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )

    @field_validator("chunk_id")
    @classmethod
    def _validate_chunk_id(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("sha256:"):
            raise ValueError("system citation chunk ID must be content-addressed")
        return value

    @model_validator(mode="after")
    def _validate_span(self) -> SystemCitation:
        if self.character_end <= self.character_start:
            raise ValueError("system citation end must follow its start")
        is_v2 = self.schema_version.endswith(".v2")
        if is_v2 != (self.exact_text is not None and self.chunk_id is not None):
            raise ValueError("system citation version and exact evidence differ")
        if self.exact_text is not None and (
            not self.exact_text
            or self.character_end - self.character_start != len(self.exact_text)
            or hashlib.sha256(self.exact_text.encode("utf-8")).hexdigest()
            != self.exact_text_sha256
        ):
            raise ValueError("system citation exact text, bounds, or hash differ")
        return self


class SystemClaim(StableModel):
    """Atomic claim emitted by the evaluated system."""

    schema_version: Literal["bijux.canon.evaluation.system-claim.v1"] = (
        "bijux.canon.evaluation.system-claim.v1"
    )
    claim_id: Identifier
    statement: NonEmptyText
    disposition: SystemClaimDisposition
    citation_ids: tuple[Identifier, ...] = ()

    @model_validator(mode="after")
    def _require_unique_citations(self) -> SystemClaim:
        if len(set(self.citation_ids)) != len(self.citation_ids):
            raise ValueError("system claim citation IDs must be unique")
        return self


class SystemOutput(StableModel):
    """Replay-addressable system answer that cannot supply its own truth labels."""

    schema_version: Literal["bijux.canon.evaluation.system-output.v1"] = (
        "bijux.canon.evaluation.system-output.v1"
    )
    output_id: Identifier
    case_id: Identifier
    runtime_run_id: Identifier
    runtime_attempt_id: Identifier
    answer: str
    disposition: SystemAnswerDisposition
    claims: tuple[SystemClaim, ...] = ()
    citations: tuple[SystemCitation, ...] = ()
    abstention_reason: str | None = None
    trace_identity_sha256: Sha256
    system_output_may_define_truth: Literal[False] = False

    @model_validator(mode="after")
    def _validate_output(self) -> SystemOutput:
        claim_ids = {claim.claim_id for claim in self.claims}
        citation_ids = {citation.citation_id for citation in self.citations}
        if len(claim_ids) != len(self.claims):
            raise ValueError("system output claim IDs must be unique")
        if len(citation_ids) != len(self.citations):
            raise ValueError("system output citation IDs must be unique")
        referenced = {
            citation_id for claim in self.claims for citation_id in claim.citation_ids
        }
        if not referenced.issubset(citation_ids):
            raise ValueError("system claim references an unknown citation")
        if self.disposition is SystemAnswerDisposition.abstained:
            if self.answer or self.claims or not self.abstention_reason:
                raise ValueError(
                    "fully abstained outputs require a reason and no answer claims"
                )
        elif self.disposition is SystemAnswerDisposition.answered and (
            not self.answer.strip() or self.abstention_reason is not None
        ):
            raise ValueError("answered outputs require an answer without abstention")
        return self


__all__ = [
    "SystemAnswerDisposition",
    "SystemCitation",
    "SystemClaim",
    "SystemClaimDisposition",
    "SystemOutput",
]
