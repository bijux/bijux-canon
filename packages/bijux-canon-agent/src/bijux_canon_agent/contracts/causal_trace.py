"""Content-addressed causal records for research-agent decisions."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json


def _artifact_id(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class CausalDecisionEvent:
    """Why one state changed, with exact causes and effects."""

    artifact_id: str
    sequence: int
    state_before_artifact_id: str
    role: str
    operation: str
    rationale: str
    observation_artifact_ids: tuple[str, ...]
    evidence_artifact_ids: tuple[str, ...]
    tool_decision_artifact_ids: tuple[str, ...]
    budget_decision_artifact_ids: tuple[str, ...]
    policy_artifact_ids: tuple[str, ...]
    output_artifact_ids: tuple[str, ...]
    operation_artifact_id: str
    transition_artifact_id: str
    state_after_artifact_id: str

    @classmethod
    def create(
        cls,
        *,
        sequence: int,
        state_before_artifact_id: str,
        role: str,
        operation: str,
        rationale: str,
        observation_artifact_ids: tuple[str, ...],
        evidence_artifact_ids: tuple[str, ...],
        tool_decision_artifact_ids: tuple[str, ...],
        budget_decision_artifact_ids: tuple[str, ...],
        policy_artifact_ids: tuple[str, ...],
        output_artifact_ids: tuple[str, ...],
        operation_artifact_id: str,
        transition_artifact_id: str,
        state_after_artifact_id: str,
    ) -> CausalDecisionEvent:
        payload = {
            "sequence": sequence,
            "state_before_artifact_id": state_before_artifact_id,
            "role": role,
            "operation": operation,
            "rationale": rationale,
            "observation_artifact_ids": list(observation_artifact_ids),
            "evidence_artifact_ids": list(evidence_artifact_ids),
            "tool_decision_artifact_ids": list(tool_decision_artifact_ids),
            "budget_decision_artifact_ids": list(budget_decision_artifact_ids),
            "policy_artifact_ids": list(policy_artifact_ids),
            "output_artifact_ids": list(output_artifact_ids),
            "operation_artifact_id": operation_artifact_id,
            "transition_artifact_id": transition_artifact_id,
            "state_after_artifact_id": state_after_artifact_id,
        }
        return cls(
            artifact_id=_artifact_id(payload),
            sequence=sequence,
            state_before_artifact_id=state_before_artifact_id,
            role=role,
            operation=operation,
            rationale=rationale,
            observation_artifact_ids=observation_artifact_ids,
            evidence_artifact_ids=evidence_artifact_ids,
            tool_decision_artifact_ids=tool_decision_artifact_ids,
            budget_decision_artifact_ids=budget_decision_artifact_ids,
            policy_artifact_ids=policy_artifact_ids,
            output_artifact_ids=output_artifact_ids,
            operation_artifact_id=operation_artifact_id,
            transition_artifact_id=transition_artifact_id,
            state_after_artifact_id=state_after_artifact_id,
        )


@dataclass(frozen=True, slots=True)
class ResearchCausalTrace:
    """Ordered causal event chain for a terminal research execution."""

    artifact_id: str
    event_artifact_ids: tuple[str, ...]
    head_artifact_id: str

    @classmethod
    def create(
        cls, events: tuple[CausalDecisionEvent, ...]
    ) -> ResearchCausalTrace:
        if not events:
            raise ValueError("causal trace requires at least one event")
        if tuple(event.sequence for event in events) != tuple(range(len(events))):
            raise ValueError("causal events must be contiguous")
        event_ids = tuple(event.artifact_id for event in events)
        payload = {
            "event_artifact_ids": list(event_ids),
            "head_artifact_id": event_ids[-1],
        }
        return cls(
            artifact_id=_artifact_id(payload),
            event_artifact_ids=event_ids,
            head_artifact_id=event_ids[-1],
        )


__all__ = ["CausalDecisionEvent", "ResearchCausalTrace"]
