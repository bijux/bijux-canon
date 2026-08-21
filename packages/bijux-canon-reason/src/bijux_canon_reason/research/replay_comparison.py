# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Replay immutable research graph events and compare adjacent attempts."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)


class ResearchChangeAuthority(StrEnum):
    """Authority responsible for one immutable research graph mutation."""

    deterministic = "deterministic"
    provider_mediated = "provider_mediated"


class ResearchGraphEventKind(StrEnum):
    """Closed mutation vocabulary for replayable research graph state."""

    claim_admitted = "claim_admitted"
    claim_retracted = "claim_retracted"
    evidence_admitted = "evidence_admitted"
    evidence_retracted = "evidence_retracted"
    decision_recorded = "decision_recorded"
    decision_superseded = "decision_superseded"


class ResearchGraphSurface(StrEnum):
    """Graph surface changed by an event or comparison entry."""

    claim = "claim"
    evidence = "evidence"
    decision = "decision"


class ResearchChangeAction(StrEnum):
    """Set-level result of an event across adjacent attempts."""

    added = "added"
    removed = "removed"


class ResearchReplayErrorCode(StrEnum):
    """Stable reasons immutable research history cannot be replayed."""

    empty_attempt_chain = "empty_attempt_chain"
    attempt_identity_mismatch = "attempt_identity_mismatch"
    event_identity_mismatch = "event_identity_mismatch"
    event_sequence_mismatch = "event_sequence_mismatch"
    event_chain_mismatch = "event_chain_mismatch"
    authority_provenance_mismatch = "authority_provenance_mismatch"
    parent_attempt_mismatch = "parent_attempt_mismatch"
    base_state_mismatch = "base_state_mismatch"
    invalid_transition = "invalid_transition"
    nonadjacent_comparison = "nonadjacent_comparison"
    unattributed_change = "unattributed_change"


class ResearchReplayError(ValueError):
    """Research history is not an immutable, replayable event chain."""

    def __init__(self, code: ResearchReplayErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class ResearchGraphEvent(StableModel):
    """One content-addressed mutation with explicit causal authority."""

    artifact_id: str
    sequence: int
    previous_event_artifact_id: str | None
    kind: ResearchGraphEventKind
    target_artifact_id: str
    authority: ResearchChangeAuthority
    deterministic_policy_artifact_id: str | None = None
    provider_provenance_artifact_id: str | None = None

    @field_validator(
        "artifact_id",
        "previous_event_artifact_id",
        "target_artifact_id",
        "deterministic_policy_artifact_id",
        "provider_provenance_artifact_id",
    )
    @classmethod
    def _validate_optional_id(cls, value: str | None) -> str | None:
        return None if value is None else require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_event(self) -> Self:
        if self.sequence <= 0:
            raise ValueError("research event sequence must be positive")
        deterministic = self.deterministic_policy_artifact_id is not None
        provider = self.provider_provenance_artifact_id is not None
        if self.authority is ResearchChangeAuthority.deterministic:
            valid_authority = deterministic and not provider
        else:
            valid_authority = provider and not deterministic
        if not valid_authority:
            raise ValueError("event authority requires exactly its matching provenance")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("research graph event identity does not match")
        return self


class ResearchReasoningAttempt(StableModel):
    """Immutable attempt inputs and its ordered graph-event delta."""

    schema_version: Literal["bijux.canon.reason.research_reasoning_attempt.v1"] = (
        "bijux.canon.reason.research_reasoning_attempt.v1"
    )
    artifact_id: str
    research_input_artifact_ids: tuple[str, ...]
    parent_attempt_artifact_id: str | None
    base_state_artifact_id: str | None
    events: tuple[ResearchGraphEvent, ...]

    @field_validator(
        "artifact_id", "parent_attempt_artifact_id", "base_state_artifact_id"
    )
    @classmethod
    def _validate_optional_id(cls, value: str | None) -> str | None:
        return None if value is None else require_artifact_id(value)

    @field_validator("research_input_artifact_ids")
    @classmethod
    def _validate_inputs(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or tuple(sorted(set(value))) != value:
            raise ValueError("attempt inputs must be non-empty, unique, and sorted")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_attempt(self) -> Self:
        if (self.parent_attempt_artifact_id is None) != (
            self.base_state_artifact_id is None
        ):
            raise ValueError("parent attempt and base state must be declared together")
        _validate_local_event_chain(self.events, as_model_error=True)
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("research reasoning attempt identity does not match")
        return self


class ReplayedResearchAttempt(StableModel):
    """Deterministically reconstructed graph state after one attempt."""

    artifact_id: str
    attempt_artifact_id: str
    parent_attempt_artifact_id: str | None
    research_input_artifact_ids: tuple[str, ...]
    event_artifact_ids: tuple[str, ...]
    claim_artifact_ids: tuple[str, ...]
    evidence_artifact_ids: tuple[str, ...]
    decision_artifact_ids: tuple[str, ...]
    deterministic_event_artifact_ids: tuple[str, ...]
    provider_mediated_event_artifact_ids: tuple[str, ...]
    state_artifact_id: str

    @field_validator(
        "artifact_id", "attempt_artifact_id", "parent_attempt_artifact_id", "state_artifact_id"
    )
    @classmethod
    def _validate_optional_id(cls, value: str | None) -> str | None:
        return None if value is None else require_artifact_id(value)

    @field_validator(
        "research_input_artifact_ids",
        "event_artifact_ids",
        "claim_artifact_ids",
        "evidence_artifact_ids",
        "decision_artifact_ids",
        "deterministic_event_artifact_ids",
        "provider_mediated_event_artifact_ids",
    )
    @classmethod
    def _validate_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if tuple(sorted(set(value))) != value:
            raise ValueError("replayed identities must be unique and sorted")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_replay(self) -> Self:
        authority_events = set(self.deterministic_event_artifact_ids) | set(
            self.provider_mediated_event_artifact_ids
        )
        if authority_events != set(self.event_artifact_ids) or set(
            self.deterministic_event_artifact_ids
        ) & set(self.provider_mediated_event_artifact_ids):
            raise ValueError("every replayed event requires exactly one authority")
        expected_state = content_artifact_id(
            {
                "claim_artifact_ids": self.claim_artifact_ids,
                "evidence_artifact_ids": self.evidence_artifact_ids,
                "decision_artifact_ids": self.decision_artifact_ids,
            }
        )
        if self.state_artifact_id != expected_state:
            raise ValueError("replayed state identity does not match graph state")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("replayed attempt identity does not match")
        return self


class ResearchChangeAttribution(StableModel):
    """One graph difference attributed to its exact mutation authority."""

    artifact_id: str
    surface: ResearchGraphSurface
    action: ResearchChangeAction
    target_artifact_id: str
    event_artifact_id: str
    authority: ResearchChangeAuthority
    authority_provenance_artifact_id: str

    @field_validator(
        "artifact_id",
        "target_artifact_id",
        "event_artifact_id",
        "authority_provenance_artifact_id",
    )
    @classmethod
    def _validate_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_attribution(self) -> Self:
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("research change attribution identity does not match")
        return self


class ResearchAttemptComparison(StableModel):
    """Exact claims, evidence, decisions, inputs, and causes changed across attempts."""

    schema_version: Literal["bijux.canon.reason.research_attempt_comparison.v1"] = (
        "bijux.canon.reason.research_attempt_comparison.v1"
    )
    artifact_id: str
    baseline_attempt_artifact_id: str
    current_attempt_artifact_id: str
    baseline_state_artifact_id: str
    current_state_artifact_id: str
    added_input_artifact_ids: tuple[str, ...]
    removed_input_artifact_ids: tuple[str, ...]
    added_claim_artifact_ids: tuple[str, ...]
    removed_claim_artifact_ids: tuple[str, ...]
    added_evidence_artifact_ids: tuple[str, ...]
    removed_evidence_artifact_ids: tuple[str, ...]
    added_decision_artifact_ids: tuple[str, ...]
    removed_decision_artifact_ids: tuple[str, ...]
    attributions: tuple[ResearchChangeAttribution, ...]
    identical_graph_state: bool

    @field_validator(
        "artifact_id",
        "baseline_attempt_artifact_id",
        "current_attempt_artifact_id",
        "baseline_state_artifact_id",
        "current_state_artifact_id",
    )
    @classmethod
    def _validate_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator(
        "added_input_artifact_ids",
        "removed_input_artifact_ids",
        "added_claim_artifact_ids",
        "removed_claim_artifact_ids",
        "added_evidence_artifact_ids",
        "removed_evidence_artifact_ids",
        "added_decision_artifact_ids",
        "removed_decision_artifact_ids",
    )
    @classmethod
    def _validate_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if tuple(sorted(set(value))) != value:
            raise ValueError("comparison identities must be unique and sorted")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_comparison(self) -> Self:
        graph_changes = {
            (surface, action, target)
            for surface, action, targets in (
                (ResearchGraphSurface.claim, ResearchChangeAction.added, self.added_claim_artifact_ids),
                (ResearchGraphSurface.claim, ResearchChangeAction.removed, self.removed_claim_artifact_ids),
                (ResearchGraphSurface.evidence, ResearchChangeAction.added, self.added_evidence_artifact_ids),
                (ResearchGraphSurface.evidence, ResearchChangeAction.removed, self.removed_evidence_artifact_ids),
                (ResearchGraphSurface.decision, ResearchChangeAction.added, self.added_decision_artifact_ids),
                (ResearchGraphSurface.decision, ResearchChangeAction.removed, self.removed_decision_artifact_ids),
            )
            for target in targets
        }
        attributed = {
            (item.surface, item.action, item.target_artifact_id)
            for item in self.attributions
        }
        if attributed != graph_changes:
            raise ValueError("every graph difference requires exactly one attribution")
        if len(attributed) != len(self.attributions):
            raise ValueError("graph differences cannot have duplicate attributions")
        if self.identical_graph_state != (not graph_changes):
            raise ValueError("identical state flag must reflect graph differences")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("research attempt comparison identity does not match")
        return self


class ResearchReasoningReplayService:
    """Reconstruct linked attempts exclusively from immutable inputs and events."""

    def replay_chain(
        self, attempts: tuple[ResearchReasoningAttempt, ...]
    ) -> tuple[ReplayedResearchAttempt, ...]:
        """Replay one root and every adjacent delta, rejecting broken history."""

        if not attempts:
            raise ResearchReplayError(
                ResearchReplayErrorCode.empty_attempt_chain,
                "research replay requires at least one immutable attempt",
            )
        replayed = []
        claims: set[str] = set()
        evidence: set[str] = set()
        decisions: set[str] = set()
        for ordinal, attempt in enumerate(attempts):
            self._verify_attempt(attempt)
            previous = replayed[-1] if replayed else None
            if previous is None:
                if attempt.parent_attempt_artifact_id is not None:
                    raise ResearchReplayError(
                        ResearchReplayErrorCode.parent_attempt_mismatch,
                        "the first replayed attempt must be a root",
                    )
            else:
                if attempt.parent_attempt_artifact_id != previous.attempt_artifact_id:
                    raise ResearchReplayError(
                        ResearchReplayErrorCode.parent_attempt_mismatch,
                        "attempt parent does not match the preceding immutable attempt",
                    )
                if attempt.base_state_artifact_id != previous.state_artifact_id:
                    raise ResearchReplayError(
                        ResearchReplayErrorCode.base_state_mismatch,
                        "attempt base state does not match the preceding replayed state",
                    )
            for event in attempt.events:
                _apply_event(event, claims, evidence, decisions)
            replayed.append(
                _replayed_attempt(
                    attempt,
                    claims=claims,
                    evidence=evidence,
                    decisions=decisions,
                )
            )
            if ordinal and replayed[-1].parent_attempt_artifact_id is None:
                raise ResearchReplayError(
                    ResearchReplayErrorCode.parent_attempt_mismatch,
                    "derived replay state lost its parent attempt",
                )
        return tuple(replayed)

    @staticmethod
    def compare(
        *,
        baseline: ReplayedResearchAttempt,
        current: ReplayedResearchAttempt,
        current_attempt: ResearchReasoningAttempt,
    ) -> ResearchAttemptComparison:
        """Compare adjacent replayed states and attribute every graph difference."""

        if (
            current.parent_attempt_artifact_id != baseline.attempt_artifact_id
            or current.attempt_artifact_id != current_attempt.artifact_id
        ):
            raise ResearchReplayError(
                ResearchReplayErrorCode.nonadjacent_comparison,
                "research comparison requires a baseline and its direct child",
            )
        changes = {
            "added_input_artifact_ids": _added(
                baseline.research_input_artifact_ids,
                current.research_input_artifact_ids,
            ),
            "removed_input_artifact_ids": _removed(
                baseline.research_input_artifact_ids,
                current.research_input_artifact_ids,
            ),
            "added_claim_artifact_ids": _added(
                baseline.claim_artifact_ids, current.claim_artifact_ids
            ),
            "removed_claim_artifact_ids": _removed(
                baseline.claim_artifact_ids, current.claim_artifact_ids
            ),
            "added_evidence_artifact_ids": _added(
                baseline.evidence_artifact_ids, current.evidence_artifact_ids
            ),
            "removed_evidence_artifact_ids": _removed(
                baseline.evidence_artifact_ids, current.evidence_artifact_ids
            ),
            "added_decision_artifact_ids": _added(
                baseline.decision_artifact_ids, current.decision_artifact_ids
            ),
            "removed_decision_artifact_ids": _removed(
                baseline.decision_artifact_ids, current.decision_artifact_ids
            ),
        }
        expected = {
            (surface, action, target)
            for surface, action, key in (
                (ResearchGraphSurface.claim, ResearchChangeAction.added, "added_claim_artifact_ids"),
                (ResearchGraphSurface.claim, ResearchChangeAction.removed, "removed_claim_artifact_ids"),
                (ResearchGraphSurface.evidence, ResearchChangeAction.added, "added_evidence_artifact_ids"),
                (ResearchGraphSurface.evidence, ResearchChangeAction.removed, "removed_evidence_artifact_ids"),
                (ResearchGraphSurface.decision, ResearchChangeAction.added, "added_decision_artifact_ids"),
                (ResearchGraphSurface.decision, ResearchChangeAction.removed, "removed_decision_artifact_ids"),
            )
            for target in changes[key]
        }
        attributions = []
        for event in current_attempt.events:
            surface, action = _event_effect(event.kind)
            key = (surface, action, event.target_artifact_id)
            if key not in expected:
                continue
            authority_id = (
                event.deterministic_policy_artifact_id
                if event.authority is ResearchChangeAuthority.deterministic
                else event.provider_provenance_artifact_id
            )
            if authority_id is None:
                raise ResearchReplayError(
                    ResearchReplayErrorCode.authority_provenance_mismatch,
                    "changed graph state lacks exact authority provenance",
                )
            payload = {
                "surface": surface.value,
                "action": action.value,
                "target_artifact_id": event.target_artifact_id,
                "event_artifact_id": event.artifact_id,
                "authority": event.authority.value,
                "authority_provenance_artifact_id": authority_id,
            }
            attributions.append(
                ResearchChangeAttribution(
                    artifact_id=content_artifact_id(payload),
                    surface=surface,
                    action=action,
                    target_artifact_id=event.target_artifact_id,
                    event_artifact_id=event.artifact_id,
                    authority=event.authority,
                    authority_provenance_artifact_id=authority_id,
                )
            )
        if {
            (item.surface, item.action, item.target_artifact_id)
            for item in attributions
        } != expected:
            raise ResearchReplayError(
                ResearchReplayErrorCode.unattributed_change,
                "every changed claim, evidence item, and decision requires an event cause",
            )
        ordered_attributions = tuple(
            sorted(attributions, key=lambda item: item.artifact_id)
        )
        payload = {
            "schema_version": "bijux.canon.reason.research_attempt_comparison.v1",
            "baseline_attempt_artifact_id": baseline.attempt_artifact_id,
            "current_attempt_artifact_id": current.attempt_artifact_id,
            "baseline_state_artifact_id": baseline.state_artifact_id,
            "current_state_artifact_id": current.state_artifact_id,
            **changes,
            "attributions": tuple(
                item.model_dump(mode="json") for item in ordered_attributions
            ),
            "identical_graph_state": not expected,
        }
        return ResearchAttemptComparison(
            artifact_id=content_artifact_id(payload),
            baseline_attempt_artifact_id=baseline.attempt_artifact_id,
            current_attempt_artifact_id=current.attempt_artifact_id,
            baseline_state_artifact_id=baseline.state_artifact_id,
            current_state_artifact_id=current.state_artifact_id,
            attributions=ordered_attributions,
            identical_graph_state=not expected,
            **changes,
        )

    @staticmethod
    def _verify_attempt(attempt: ResearchReasoningAttempt) -> None:
        for event in attempt.events:
            try:
                ResearchGraphEvent.model_validate(event.model_dump(mode="python"))
            except ValueError as error:
                message = str(error)
                code = (
                    ResearchReplayErrorCode.authority_provenance_mismatch
                    if "authority" in message
                    else ResearchReplayErrorCode.event_identity_mismatch
                )
                raise ResearchReplayError(code, message) from error
        _validate_local_event_chain(attempt.events, as_model_error=False)
        expected = content_artifact_id(
            attempt.model_dump(mode="json", exclude={"artifact_id"})
        )
        if attempt.artifact_id != expected:
            raise ResearchReplayError(
                ResearchReplayErrorCode.attempt_identity_mismatch,
                "research attempt identity does not match immutable inputs and events",
            )


def create_research_graph_event(
    *,
    sequence: int,
    previous_event_artifact_id: str | None,
    kind: ResearchGraphEventKind,
    target_artifact_id: str,
    authority: ResearchChangeAuthority,
    authority_provenance_artifact_id: str,
) -> ResearchGraphEvent:
    """Create one graph event with the matching authority provenance field."""

    deterministic_id = (
        authority_provenance_artifact_id
        if authority is ResearchChangeAuthority.deterministic
        else None
    )
    provider_id = (
        authority_provenance_artifact_id
        if authority is ResearchChangeAuthority.provider_mediated
        else None
    )
    payload = {
        "sequence": sequence,
        "previous_event_artifact_id": previous_event_artifact_id,
        "kind": kind.value,
        "target_artifact_id": target_artifact_id,
        "authority": authority.value,
        "deterministic_policy_artifact_id": deterministic_id,
        "provider_provenance_artifact_id": provider_id,
    }
    return ResearchGraphEvent(
        artifact_id=content_artifact_id(payload),
        sequence=sequence,
        previous_event_artifact_id=previous_event_artifact_id,
        kind=kind,
        target_artifact_id=target_artifact_id,
        authority=authority,
        deterministic_policy_artifact_id=deterministic_id,
        provider_provenance_artifact_id=provider_id,
    )


def create_research_reasoning_attempt(
    *,
    research_input_artifact_ids: tuple[str, ...],
    events: tuple[ResearchGraphEvent, ...],
    parent_attempt_artifact_id: str | None = None,
    base_state_artifact_id: str | None = None,
) -> ResearchReasoningAttempt:
    """Create one immutable root or adjacent research reasoning attempt."""

    inputs = tuple(sorted(set(research_input_artifact_ids)))
    payload = {
        "schema_version": "bijux.canon.reason.research_reasoning_attempt.v1",
        "research_input_artifact_ids": inputs,
        "parent_attempt_artifact_id": parent_attempt_artifact_id,
        "base_state_artifact_id": base_state_artifact_id,
        "events": tuple(item.model_dump(mode="json") for item in events),
    }
    return ResearchReasoningAttempt(
        artifact_id=content_artifact_id(payload),
        research_input_artifact_ids=inputs,
        parent_attempt_artifact_id=parent_attempt_artifact_id,
        base_state_artifact_id=base_state_artifact_id,
        events=events,
    )


def _validate_local_event_chain(
    events: tuple[ResearchGraphEvent, ...], *, as_model_error: bool
) -> None:
    expected_sequence = tuple(range(1, len(events) + 1))
    if tuple(item.sequence for item in events) != expected_sequence:
        if as_model_error:
            raise ValueError("attempt event sequence must begin at one and be contiguous")
        raise ResearchReplayError(
            ResearchReplayErrorCode.event_sequence_mismatch,
            "attempt event sequence must begin at one and be contiguous",
        )
    for ordinal, event in enumerate(events):
        expected_previous = None if ordinal == 0 else events[ordinal - 1].artifact_id
        if event.previous_event_artifact_id != expected_previous:
            if as_model_error:
                raise ValueError("attempt event hash chain is broken")
            raise ResearchReplayError(
                ResearchReplayErrorCode.event_chain_mismatch,
                "attempt event hash chain is broken",
            )


def _apply_event(
    event: ResearchGraphEvent,
    claims: set[str],
    evidence: set[str],
    decisions: set[str],
) -> None:
    surface, action = _event_effect(event.kind)
    target_set = {
        ResearchGraphSurface.claim: claims,
        ResearchGraphSurface.evidence: evidence,
        ResearchGraphSurface.decision: decisions,
    }[surface]
    if action is ResearchChangeAction.added:
        invalid = event.target_artifact_id in target_set
        if not invalid:
            target_set.add(event.target_artifact_id)
    else:
        invalid = event.target_artifact_id not in target_set
        if not invalid:
            target_set.remove(event.target_artifact_id)
    if invalid:
        raise ResearchReplayError(
            ResearchReplayErrorCode.invalid_transition,
            f"event {event.kind.value} cannot apply to current graph state",
        )


def _event_effect(
    kind: ResearchGraphEventKind,
) -> tuple[ResearchGraphSurface, ResearchChangeAction]:
    return {
        ResearchGraphEventKind.claim_admitted: (
            ResearchGraphSurface.claim,
            ResearchChangeAction.added,
        ),
        ResearchGraphEventKind.claim_retracted: (
            ResearchGraphSurface.claim,
            ResearchChangeAction.removed,
        ),
        ResearchGraphEventKind.evidence_admitted: (
            ResearchGraphSurface.evidence,
            ResearchChangeAction.added,
        ),
        ResearchGraphEventKind.evidence_retracted: (
            ResearchGraphSurface.evidence,
            ResearchChangeAction.removed,
        ),
        ResearchGraphEventKind.decision_recorded: (
            ResearchGraphSurface.decision,
            ResearchChangeAction.added,
        ),
        ResearchGraphEventKind.decision_superseded: (
            ResearchGraphSurface.decision,
            ResearchChangeAction.removed,
        ),
    }[kind]


def _replayed_attempt(
    attempt: ResearchReasoningAttempt,
    *,
    claims: set[str],
    evidence: set[str],
    decisions: set[str],
) -> ReplayedResearchAttempt:
    claim_ids = tuple(sorted(claims))
    evidence_ids = tuple(sorted(evidence))
    decision_ids = tuple(sorted(decisions))
    state_id = content_artifact_id(
        {
            "claim_artifact_ids": claim_ids,
            "evidence_artifact_ids": evidence_ids,
            "decision_artifact_ids": decision_ids,
        }
    )
    event_ids = tuple(sorted(item.artifact_id for item in attempt.events))
    deterministic_ids = tuple(
        sorted(
            item.artifact_id
            for item in attempt.events
            if item.authority is ResearchChangeAuthority.deterministic
        )
    )
    provider_ids = tuple(
        sorted(
            item.artifact_id
            for item in attempt.events
            if item.authority is ResearchChangeAuthority.provider_mediated
        )
    )
    payload = {
        "attempt_artifact_id": attempt.artifact_id,
        "parent_attempt_artifact_id": attempt.parent_attempt_artifact_id,
        "research_input_artifact_ids": attempt.research_input_artifact_ids,
        "event_artifact_ids": event_ids,
        "claim_artifact_ids": claim_ids,
        "evidence_artifact_ids": evidence_ids,
        "decision_artifact_ids": decision_ids,
        "deterministic_event_artifact_ids": deterministic_ids,
        "provider_mediated_event_artifact_ids": provider_ids,
        "state_artifact_id": state_id,
    }
    return ReplayedResearchAttempt(artifact_id=content_artifact_id(payload), **payload)


def _added(baseline: tuple[str, ...], current: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(set(current) - set(baseline)))


def _removed(baseline: tuple[str, ...], current: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(set(baseline) - set(current)))


__all__ = [
    "ReplayedResearchAttempt",
    "ResearchAttemptComparison",
    "ResearchChangeAction",
    "ResearchChangeAttribution",
    "ResearchChangeAuthority",
    "ResearchGraphEvent",
    "ResearchGraphEventKind",
    "ResearchGraphSurface",
    "ResearchReasoningAttempt",
    "ResearchReasoningReplayService",
    "ResearchReplayError",
    "ResearchReplayErrorCode",
    "create_research_graph_event",
    "create_research_reasoning_attempt",
]
