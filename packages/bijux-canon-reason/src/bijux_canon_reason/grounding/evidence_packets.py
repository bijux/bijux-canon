# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Build bounded evidence packets without weakening citation provenance."""

from __future__ import annotations

from collections import Counter
from enum import StrEnum
import hashlib
import math
import re
from typing import ClassVar, Protocol, Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.fingerprints import fingerprint_obj
from bijux_canon_reason.core.models.base import StableModel

_ARTIFACT_ID = re.compile(r"sha256:[0-9a-f]{64}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_TOKEN = re.compile(r"\w+|[^\w\s]", flags=re.UNICODE)

LocatorValue = str | int


def _require_artifact_id(value: str) -> str:
    if _ARTIFACT_ID.fullmatch(value) is None:
        raise ValueError("artifact identity must be sha256:<64 lowercase hex>")
    return value


def _require_sha256(value: str) -> str:
    if _SHA256.fullmatch(value) is None:
        raise ValueError("content identity must be 64 lowercase hex characters")
    return value


def _content_id(value: object) -> str:
    return f"sha256:{fingerprint_obj(value)}"


class EvidenceTrust(StrEnum):
    """Trust classification applied to all retrieved source content."""

    retrieved_untrusted = "retrieved_untrusted"


class PacketCompleteness(StrEnum):
    """Whether selection admitted all, some, or none of the candidates."""

    complete = "complete"
    bounded = "bounded"
    insufficient = "insufficient"


class SelectionDisposition(StrEnum):
    """Disposition of one citation-ready retrieval candidate."""

    selected = "selected"
    omitted = "omitted"


class OmissionReason(StrEnum):
    """Stable reasons why a candidate was not admitted to a packet."""

    none = "none"
    duplicate = "duplicate"
    token_budget = "token_budget"
    citation_budget = "citation_budget"
    claim_budget = "claim_budget"
    source_limit = "source_limit"
    section_limit = "section_limit"


class EvidencePacketErrorCode(StrEnum):
    """Stable failures raised before evidence selection can proceed."""

    identity_collision = "identity_collision"
    invalid_token_count = "invalid_token_count"
    token_counter_mismatch = "token_counter_mismatch"


class EvidencePacketError(ValueError):
    """Evidence candidates or packet policy cannot be applied safely."""

    def __init__(self, code: EvidencePacketErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class TokenCounter(Protocol):
    """Count tokens with a named, reproducible algorithm."""

    identifier: str

    def count(self, text: str) -> int:
        """Return the number of budget units in ``text``."""


class UnicodeLexicalTokenCounter:
    """Dependency-free Unicode word-and-punctuation counter."""

    identifier: ClassVar[str] = "unicode-lexical-v1"

    def count(self, text: str) -> int:
        """Count every Unicode word or punctuation symbol."""

        return len(_TOKEN.findall(text))


class ImmutableEvidenceLocator(StableModel):
    """Complete immutable source locator transported with quoted text."""

    artifact_id: str
    source_artifact_id: str
    source_uri: str
    source_content_sha256: str
    scheme: str
    selectors: tuple[tuple[str, LocatorValue], ...]

    @field_validator("artifact_id", "source_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return _require_artifact_id(value)

    @field_validator("source_content_sha256")
    @classmethod
    def _validate_content_id(cls, value: str) -> str:
        return _require_sha256(value)

    @field_validator("source_uri", "scheme")
    @classmethod
    def _validate_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("locator fields must not be empty")
        return value

    @field_validator("selectors")
    @classmethod
    def _validate_selectors(
        cls, value: tuple[tuple[str, LocatorValue], ...]
    ) -> tuple[tuple[str, LocatorValue], ...]:
        names = tuple(name for name, _ in value)
        if (
            not names
            or any(not name for name in names)
            or len(names) != len(set(names))
        ):
            raise ValueError("locator requires unique named selectors")
        return value


class CitationEvidence(StableModel):
    """Citation-ready retrieved text bound to its immutable source locator."""

    artifact_id: str
    chunk_artifact_id: str
    retrieval_artifact_id: str
    document_id: str
    source_id: str
    section_path: tuple[str, ...]
    locator: ImmutableEvidenceLocator
    exact_text: str
    exact_text_sha256: str
    rank: int
    relevance_score: float
    claim_keys: tuple[str, ...] = ()
    trust: EvidenceTrust = EvidenceTrust.retrieved_untrusted

    @field_validator("artifact_id", "chunk_artifact_id", "retrieval_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return _require_artifact_id(value)

    @field_validator("exact_text_sha256")
    @classmethod
    def _validate_text_hash(cls, value: str) -> str:
        return _require_sha256(value)

    @field_validator("document_id", "source_id", "exact_text")
    @classmethod
    def _validate_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("citation evidence fields must not be empty")
        return value

    @field_validator("section_path")
    @classmethod
    def _validate_section_path(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or any(not part for part in value):
            raise ValueError("citation evidence requires a non-empty section path")
        return value

    @field_validator("rank")
    @classmethod
    def _validate_rank(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("citation rank must be positive")
        return value

    @field_validator("relevance_score")
    @classmethod
    def _validate_score(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("citation relevance score must be finite")
        return value

    @field_validator("claim_keys")
    @classmethod
    def _validate_claim_keys(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item for item in value) or len(value) != len(set(value)):
            raise ValueError("claim keys must be unique and non-empty")
        return value

    @model_validator(mode="after")
    def _verify_text_identity(self) -> Self:
        if hashlib.sha256(self.exact_text.encode("utf-8")).hexdigest() != (
            self.exact_text_sha256
        ):
            raise ValueError("exact text does not match exact_text_sha256")
        return self


class EvidencePacketPolicy(StableModel):
    """Explicit evidence, claim, source, section, and token limits."""

    token_budget: int
    citation_budget: int
    claim_budget: int
    max_per_source: int
    max_per_section: int
    token_counter_id: str = UnicodeLexicalTokenCounter.identifier

    @field_validator(
        "token_budget",
        "citation_budget",
        "claim_budget",
        "max_per_source",
        "max_per_section",
    )
    @classmethod
    def _validate_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("evidence packet limits must be positive")
        return value

    @field_validator("token_counter_id")
    @classmethod
    def _validate_counter_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("token counter identity must not be empty")
        return value

    @property
    def artifact_id(self) -> str:
        """Return the content identity of this selection policy."""

        return _content_id(self.model_dump(mode="json"))


class EvidenceSelectionDecision(StableModel):
    """Auditable admission or omission decision for one candidate."""

    evidence_artifact_id: str
    locator_artifact_id: str
    disposition: SelectionDisposition
    reason: OmissionReason
    rationale: str
    token_count: int
    selection_order: int | None

    @field_validator("evidence_artifact_id", "locator_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return _require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_disposition(self) -> Self:
        if self.token_count <= 0 or not self.rationale.strip():
            raise ValueError("selection decision requires tokens and rationale")
        if self.disposition is SelectionDisposition.selected:
            if self.reason is not OmissionReason.none or self.selection_order is None:
                raise ValueError(
                    "selected evidence requires order and no omission reason"
                )
        elif self.reason is OmissionReason.none or self.selection_order is not None:
            raise ValueError(
                "omitted evidence requires an omission reason and no order"
            )
        return self


class EvidencePacket(StableModel):
    """Content-addressed bounded evidence with complete selection accounting."""

    schema_version: str = "bijux.canon.reason.evidence_packet.v1"
    artifact_id: str
    question_artifact_id: str
    scope_artifact_id: str
    retrieval_trace_artifact_ids: tuple[str, ...]
    selection_policy_artifact_id: str
    selected: tuple[CitationEvidence, ...]
    decisions: tuple[EvidenceSelectionDecision, ...]
    observed_tokens: int
    covered_claim_keys: tuple[str, ...]
    source_count: int
    completeness: PacketCompleteness

    @field_validator(
        "artifact_id",
        "question_artifact_id",
        "scope_artifact_id",
        "selection_policy_artifact_id",
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return _require_artifact_id(value)

    @field_validator("retrieval_trace_artifact_ids")
    @classmethod
    def _validate_trace_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or len(value) != len(set(value)):
            raise ValueError("packet requires unique retrieval trace identities")
        return tuple(_require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_packet(self) -> Self:
        selected_ids = tuple(item.artifact_id for item in self.selected)
        admitted = tuple(
            decision.evidence_artifact_id
            for decision in self.decisions
            if decision.disposition is SelectionDisposition.selected
        )
        if selected_ids != admitted:
            raise ValueError("selected evidence and admission decisions must agree")
        if self.observed_tokens != sum(
            decision.token_count
            for decision in self.decisions
            if decision.disposition is SelectionDisposition.selected
        ):
            raise ValueError("observed token count does not match selected evidence")
        sources = {item.source_id for item in self.selected}
        if self.source_count != len(sources):
            raise ValueError("packet source count does not match selected evidence")
        claims = tuple(
            sorted({item for evidence in self.selected for item in evidence.claim_keys})
        )
        if self.covered_claim_keys != claims:
            raise ValueError("covered claims do not match selected evidence")
        expected = PacketCompleteness.complete
        if not self.selected:
            expected = PacketCompleteness.insufficient
        elif any(
            decision.disposition is SelectionDisposition.omitted
            for decision in self.decisions
        ):
            expected = PacketCompleteness.bounded
        if self.completeness is not expected:
            raise ValueError("packet completeness does not match its decisions")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != _content_id(payload):
            raise ValueError("packet artifact identity does not match its payload")
        return self


class EvidencePacketBuilder:
    """Select diverse citation evidence with deterministic fail-closed limits."""

    def __init__(
        self,
        policy: EvidencePacketPolicy,
        *,
        token_counter: TokenCounter | None = None,
    ) -> None:
        self._policy = policy
        self._token_counter = token_counter or UnicodeLexicalTokenCounter()
        if self._token_counter.identifier != policy.token_counter_id:
            raise EvidencePacketError(
                EvidencePacketErrorCode.token_counter_mismatch,
                "token counter identity does not match evidence packet policy",
            )

    def build(
        self,
        *,
        question_artifact_id: str,
        scope_artifact_id: str,
        retrieval_trace_artifact_ids: tuple[str, ...],
        candidates: tuple[CitationEvidence, ...],
    ) -> EvidencePacket:
        """Build one packet while retaining every admission and omission decision."""

        _require_artifact_id(question_artifact_id)
        _require_artifact_id(scope_artifact_id)
        if not retrieval_trace_artifact_ids:
            raise ValueError("at least one retrieval trace identity is required")
        for trace_id in retrieval_trace_artifact_ids:
            _require_artifact_id(trace_id)

        unique, duplicate_decisions = self._deduplicate(candidates)
        selected: list[CitationEvidence] = []
        decisions: list[EvidenceSelectionDecision] = []
        used_tokens = 0
        covered_claims: set[str] = set()
        source_counts: Counter[str] = Counter()
        section_counts: Counter[tuple[str, ...]] = Counter()

        remaining = list(unique)
        while remaining:
            remaining.sort(
                key=lambda item: (
                    not bool(set(item.claim_keys) - covered_claims),
                    source_counts[item.source_id] > 0,
                    section_counts[item.section_path] > 0,
                    item.rank,
                    -item.relevance_score,
                    item.artifact_id,
                )
            )
            candidate = remaining.pop(0)
            token_count = self._count(candidate.exact_text)
            reason = self._omission_reason(
                candidate=candidate,
                token_count=token_count,
                selected_count=len(selected),
                used_tokens=used_tokens,
                covered_claims=covered_claims,
                source_counts=source_counts,
                section_counts=section_counts,
            )
            if reason is not OmissionReason.none:
                decisions.append(self._decision(candidate, token_count, reason=reason))
                continue

            selected.append(candidate)
            used_tokens += token_count
            adds_source = source_counts[candidate.source_id] == 0
            adds_section = section_counts[candidate.section_path] == 0
            added_claims = tuple(sorted(set(candidate.claim_keys) - covered_claims))
            covered_claims.update(candidate.claim_keys)
            source_counts[candidate.source_id] += 1
            section_counts[candidate.section_path] += 1
            decisions.append(
                EvidenceSelectionDecision(
                    evidence_artifact_id=candidate.artifact_id,
                    locator_artifact_id=candidate.locator.artifact_id,
                    disposition=SelectionDisposition.selected,
                    reason=OmissionReason.none,
                    rationale=(
                        f"selected retrieval rank {candidate.rank} within all limits; "
                        f"adds_source={str(adds_source).lower()}, "
                        f"adds_section={str(adds_section).lower()}, "
                        f"added_claim_keys={','.join(added_claims) or 'none'}"
                    ),
                    token_count=token_count,
                    selection_order=len(selected),
                )
            )

        decisions.extend(duplicate_decisions)
        completeness = PacketCompleteness.complete
        if not selected:
            completeness = PacketCompleteness.insufficient
        elif any(
            item.disposition is SelectionDisposition.omitted for item in decisions
        ):
            completeness = PacketCompleteness.bounded

        payload = {
            "schema_version": "bijux.canon.reason.evidence_packet.v1",
            "question_artifact_id": question_artifact_id,
            "scope_artifact_id": scope_artifact_id,
            "retrieval_trace_artifact_ids": retrieval_trace_artifact_ids,
            "selection_policy_artifact_id": self._policy.artifact_id,
            "selected": tuple(item.model_dump(mode="json") for item in selected),
            "decisions": tuple(item.model_dump(mode="json") for item in decisions),
            "observed_tokens": used_tokens,
            "covered_claim_keys": tuple(sorted(covered_claims)),
            "source_count": len(source_counts),
            "completeness": completeness.value,
        }
        return EvidencePacket(
            artifact_id=_content_id(payload),
            question_artifact_id=question_artifact_id,
            scope_artifact_id=scope_artifact_id,
            retrieval_trace_artifact_ids=retrieval_trace_artifact_ids,
            selection_policy_artifact_id=self._policy.artifact_id,
            selected=tuple(selected),
            decisions=tuple(decisions),
            observed_tokens=used_tokens,
            covered_claim_keys=tuple(sorted(covered_claims)),
            source_count=len(source_counts),
            completeness=completeness,
        )

    def _deduplicate(
        self, candidates: tuple[CitationEvidence, ...]
    ) -> tuple[tuple[CitationEvidence, ...], tuple[EvidenceSelectionDecision, ...]]:
        unique: dict[str, CitationEvidence] = {}
        duplicates: list[EvidenceSelectionDecision] = []
        for candidate in candidates:
            previous = unique.get(candidate.artifact_id)
            if previous is None:
                unique[candidate.artifact_id] = candidate
                continue
            if previous != candidate:
                raise EvidencePacketError(
                    EvidencePacketErrorCode.identity_collision,
                    "one evidence identity resolves to conflicting citation payloads",
                )
            token_count = self._count(candidate.exact_text)
            duplicates.append(
                self._decision(candidate, token_count, reason=OmissionReason.duplicate)
            )
        return tuple(unique.values()), tuple(duplicates)

    def _count(self, text: str) -> int:
        token_count = self._token_counter.count(text)
        if token_count <= 0:
            raise EvidencePacketError(
                EvidencePacketErrorCode.invalid_token_count,
                "token counter must return a positive count for non-empty evidence",
            )
        return token_count

    def _omission_reason(
        self,
        *,
        candidate: CitationEvidence,
        token_count: int,
        selected_count: int,
        used_tokens: int,
        covered_claims: set[str],
        source_counts: Counter[str],
        section_counts: Counter[tuple[str, ...]],
    ) -> OmissionReason:
        if selected_count >= self._policy.citation_budget:
            return OmissionReason.citation_budget
        if used_tokens + token_count > self._policy.token_budget:
            return OmissionReason.token_budget
        if len(covered_claims | set(candidate.claim_keys)) > self._policy.claim_budget:
            return OmissionReason.claim_budget
        if source_counts[candidate.source_id] >= self._policy.max_per_source:
            return OmissionReason.source_limit
        if section_counts[candidate.section_path] >= self._policy.max_per_section:
            return OmissionReason.section_limit
        return OmissionReason.none

    @staticmethod
    def _decision(
        candidate: CitationEvidence,
        token_count: int,
        *,
        reason: OmissionReason,
    ) -> EvidenceSelectionDecision:
        return EvidenceSelectionDecision(
            evidence_artifact_id=candidate.artifact_id,
            locator_artifact_id=candidate.locator.artifact_id,
            disposition=SelectionDisposition.omitted,
            reason=reason,
            rationale=f"omitted citation-ready evidence because {reason.value} was reached",
            token_count=token_count,
            selection_order=None,
        )


__all__ = [
    "CitationEvidence",
    "EvidencePacket",
    "EvidencePacketBuilder",
    "EvidencePacketError",
    "EvidencePacketErrorCode",
    "EvidencePacketPolicy",
    "EvidenceSelectionDecision",
    "EvidenceTrust",
    "ImmutableEvidenceLocator",
    "OmissionReason",
    "PacketCompleteness",
    "SelectionDisposition",
    "TokenCounter",
    "UnicodeLexicalTokenCounter",
]
