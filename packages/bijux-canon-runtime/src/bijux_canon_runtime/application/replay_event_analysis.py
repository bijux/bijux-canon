"""Helpers for analyzing replay-related execution events."""

from __future__ import annotations

from collections.abc import Iterable

from bijux_canon_runtime.model.execution.execution_steps import ExecutionSteps
from bijux_canon_runtime.model.execution.resolved_step import ResolvedStep
from bijux_canon_runtime.model.identifiers.execution_event import ExecutionEvent
from bijux_canon_runtime.ontology.public import EventType


def first_divergent_step(plan: ExecutionSteps, diffs: dict[str, object]) -> int:
    """Resolve the earliest step implicated by the replay diff payload."""
    candidates: list[int] = []
    missing = diffs.get("missing_step_end")
    if isinstance(missing, list):
        candidates.extend(int(value) for value in missing)
    failed = diffs.get("failed_steps")
    if isinstance(failed, list):
        candidates.extend(int(value) for value in failed)
    if candidates:
        return min(candidates)
    if plan.steps:
        return int(plan.steps[0].step_index)
    return 0


def missing_step_end(
    events: Iterable[ExecutionEvent], steps: Iterable[ResolvedStep]
) -> set[int]:
    """Find planned steps that never reached a successful step-end event."""
    expected_steps = {step.step_index for step in steps}
    ended = {
        event.step_index for event in events if event.event_type == EventType.STEP_END
    }
    failed = failed_steps(events)
    return expected_steps.difference(ended.union(failed))


def failed_steps(events: Iterable[ExecutionEvent]) -> set[int]:
    """Collect the step indexes terminated by failure events."""
    failure_events = {
        EventType.REASONING_FAILED,
        EventType.RETRIEVAL_FAILED,
        EventType.STEP_FAILED,
        EventType.VERIFICATION_FAIL,
    }
    return {event.step_index for event in events if event.event_type in failure_events}


def human_intervention_events(events: Iterable[ExecutionEvent]) -> list[int]:
    """Collect event indexes marked as human intervention."""
    return [
        event.event_index
        for event in events
        if event.event_type == EventType.HUMAN_INTERVENTION
    ]


__all__ = [
    "failed_steps",
    "first_divergent_step",
    "human_intervention_events",
    "missing_step_end",
]
