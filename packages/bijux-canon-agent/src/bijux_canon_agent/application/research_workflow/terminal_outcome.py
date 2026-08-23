"""Typed terminal outcomes and exact remaining work for installed research."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json


def _artifact_id(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _require_artifact_id(value: str, field: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{field} must be a SHA-256 artifact ID")


class InstalledResearchTerminalKind(StrEnum):
    """Disjoint public dispositions for one installed research attempt."""

    CONVERGED = "converged"
    ABSTAINED = "abstained"
    INCOMPLETE_BUDGET = "incomplete_budget"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class RemainingResearchWork:
    """Exact unresolved work retained instead of claiming false completion."""

    artifact_id: str
    unsatisfied_requirement_artifact_ids: tuple[str, ...]
    unresolved_evidence_artifact_ids: tuple[str, ...]
    unresolved_gap_artifact_ids: tuple[str, ...]
    unsearched_important_claim_artifact_ids: tuple[str, ...]
    descriptions: tuple[str, ...]

    def __post_init__(self) -> None:
        identity_groups = (
            self.unsatisfied_requirement_artifact_ids,
            self.unresolved_evidence_artifact_ids,
            self.unresolved_gap_artifact_ids,
            self.unsearched_important_claim_artifact_ids,
        )
        if any(len(items) != len(set(items)) for items in identity_groups):
            raise ValueError("remaining research identities must be unique")
        for items in identity_groups:
            for artifact_id in items:
                _require_artifact_id(artifact_id, "remaining research work")
        if len(self.descriptions) != len(set(self.descriptions)) or any(
            not item or item != " ".join(item.split()) for item in self.descriptions
        ):
            raise ValueError("remaining research descriptions must be normalized")
        if self.artifact_id != _artifact_id(self._payload()):
            raise ValueError("remaining research work identity does not match")

    @property
    def pending(self) -> bool:
        """Return whether any declared work remains."""
        return any(
            (
                self.unsatisfied_requirement_artifact_ids,
                self.unresolved_evidence_artifact_ids,
                self.unresolved_gap_artifact_ids,
                self.unsearched_important_claim_artifact_ids,
            )
        )

    @classmethod
    def create(
        cls,
        *,
        unsatisfied_requirement_artifact_ids: tuple[str, ...] = (),
        unresolved_evidence_artifact_ids: tuple[str, ...] = (),
        unresolved_gap_artifact_ids: tuple[str, ...] = (),
        unsearched_important_claim_artifact_ids: tuple[str, ...] = (),
        descriptions: tuple[str, ...] = (),
    ) -> RemainingResearchWork:
        normalized_descriptions = tuple(
            dict.fromkeys(
                " ".join(item.split()) for item in descriptions if item.strip()
            )
        )
        values = {
            "unsatisfied_requirement_artifact_ids": tuple(
                dict.fromkeys(unsatisfied_requirement_artifact_ids)
            ),
            "unresolved_evidence_artifact_ids": tuple(
                dict.fromkeys(unresolved_evidence_artifact_ids)
            ),
            "unresolved_gap_artifact_ids": tuple(
                dict.fromkeys(unresolved_gap_artifact_ids)
            ),
            "unsearched_important_claim_artifact_ids": tuple(
                dict.fromkeys(unsearched_important_claim_artifact_ids)
            ),
            "descriptions": normalized_descriptions,
        }
        payload = {key: list(value) for key, value in values.items()}
        return cls(artifact_id=_artifact_id(payload), **values)

    def _payload(self) -> dict[str, object]:
        return {
            "unsatisfied_requirement_artifact_ids": list(
                self.unsatisfied_requirement_artifact_ids
            ),
            "unresolved_evidence_artifact_ids": list(
                self.unresolved_evidence_artifact_ids
            ),
            "unresolved_gap_artifact_ids": list(self.unresolved_gap_artifact_ids),
            "unsearched_important_claim_artifact_ids": list(
                self.unsearched_important_claim_artifact_ids
            ),
            "descriptions": list(self.descriptions),
        }

    def to_record(self) -> dict[str, object]:
        """Return a canonical JSON-compatible record."""
        return {"artifact_id": self.artifact_id, **self._payload()}


@dataclass(frozen=True, slots=True)
class InstalledResearchTerminalOutcome:
    """One typed terminal disposition bound to convergence and remaining work."""

    artifact_id: str
    kind: InstalledResearchTerminalKind
    convergence_artifact_id: str
    convergence_outcome: str
    remaining_work: RemainingResearchWork
    exhausted_budget_dimensions: tuple[str, ...]
    cancellation_artifact_id: str | None
    failure_artifact_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_artifact_id(self.convergence_artifact_id, "research convergence")
        if self.cancellation_artifact_id is not None:
            _require_artifact_id(self.cancellation_artifact_id, "research cancellation")
        for artifact_id in self.failure_artifact_ids:
            _require_artifact_id(artifact_id, "research failure")
        if not self.convergence_outcome or any(
            not item or item != " ".join(item.split())
            for item in self.exhausted_budget_dimensions
        ):
            raise ValueError("research terminal semantics are invalid")
        if self.kind is InstalledResearchTerminalKind.CONVERGED and (
            self.remaining_work.pending
            or self.exhausted_budget_dimensions
            or self.cancellation_artifact_id is not None
            or self.failure_artifact_ids
        ):
            raise ValueError("converged research cannot retain incomplete state")
        if self.kind is InstalledResearchTerminalKind.INCOMPLETE_BUDGET and (
            not self.exhausted_budget_dimensions or not self.remaining_work.pending
        ):
            raise ValueError("incomplete-budget research must name budget and work")
        if self.kind is InstalledResearchTerminalKind.CANCELLED and (
            self.cancellation_artifact_id is None
        ):
            raise ValueError("cancelled research requires cancellation identity")
        if self.kind is InstalledResearchTerminalKind.FAILED and not (
            self.failure_artifact_ids
        ):
            raise ValueError("failed research requires failure identity")
        if self.artifact_id != _artifact_id(self._payload()):
            raise ValueError("research terminal outcome identity does not match")

    @classmethod
    def create(
        cls,
        *,
        kind: InstalledResearchTerminalKind,
        convergence_artifact_id: str,
        convergence_outcome: str,
        remaining_work: RemainingResearchWork,
        exhausted_budget_dimensions: tuple[str, ...] = (),
        cancellation_artifact_id: str | None = None,
        failure_artifact_ids: tuple[str, ...] = (),
    ) -> InstalledResearchTerminalOutcome:
        normalized_outcome = " ".join(convergence_outcome.split())
        exhausted = tuple(dict.fromkeys(exhausted_budget_dimensions))
        failures = tuple(dict.fromkeys(failure_artifact_ids))
        payload = {
            "kind": kind.value,
            "convergence_artifact_id": convergence_artifact_id,
            "convergence_outcome": normalized_outcome,
            "remaining_work_artifact_id": remaining_work.artifact_id,
            "exhausted_budget_dimensions": list(exhausted),
            "cancellation_artifact_id": cancellation_artifact_id,
            "failure_artifact_ids": list(failures),
        }
        return cls(
            artifact_id=_artifact_id(payload),
            kind=kind,
            convergence_artifact_id=convergence_artifact_id,
            convergence_outcome=normalized_outcome,
            remaining_work=remaining_work,
            exhausted_budget_dimensions=exhausted,
            cancellation_artifact_id=cancellation_artifact_id,
            failure_artifact_ids=failures,
        )

    def _payload(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "convergence_artifact_id": self.convergence_artifact_id,
            "convergence_outcome": self.convergence_outcome,
            "remaining_work_artifact_id": self.remaining_work.artifact_id,
            "exhausted_budget_dimensions": list(self.exhausted_budget_dimensions),
            "cancellation_artifact_id": self.cancellation_artifact_id,
            "failure_artifact_ids": list(self.failure_artifact_ids),
        }

    def to_record(self) -> dict[str, object]:
        """Return a canonical JSON-compatible terminal record."""
        return {
            "artifact_id": self.artifact_id,
            **self._payload(),
            "remaining_work": self.remaining_work.to_record(),
        }


__all__ = [
    "InstalledResearchTerminalKind",
    "InstalledResearchTerminalOutcome",
    "RemainingResearchWork",
]
