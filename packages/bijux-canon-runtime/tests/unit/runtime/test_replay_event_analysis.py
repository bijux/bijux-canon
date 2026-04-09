from __future__ import annotations

from types import SimpleNamespace

from bijux_canon_runtime.application.replay_event_analysis import (
    failed_steps,
    first_divergent_step,
    human_intervention_events,
)
from bijux_canon_runtime.model.identifiers.execution_event import ExecutionEvent
from bijux_canon_runtime.ontology import CausalityTag
from bijux_canon_runtime.ontology.public import (
    EventType,
)


def _event(event_index: int, step_index: int, event_type: EventType) -> ExecutionEvent:
    return ExecutionEvent(
        spec_version="v1",
        event_index=event_index,
        step_index=step_index,
        event_type=event_type,
        causality_tag=CausalityTag.AGENT,
        timestamp_utc="2026-01-01T00:00:00Z",
        payload={"event_type": event_type.value},
        payload_hash="hash",
    )


def test_failed_steps_collects_all_failure_event_indexes() -> None:
    events = [
        _event(0, 1, EventType.STEP_FAILED),
        _event(1, 2, EventType.VERIFICATION_FAIL),
        _event(2, 3, EventType.STEP_END),
    ]

    assert failed_steps(events) == {1, 2}


def test_human_intervention_events_returns_event_indexes() -> None:
    events = [
        _event(3, 1, EventType.HUMAN_INTERVENTION),
        _event(7, 2, EventType.STEP_END),
    ]

    assert human_intervention_events(events) == [3]


def test_first_divergent_step_prefers_smallest_failure_candidate() -> None:
    assert (
        first_divergent_step(
            SimpleNamespace(steps=[SimpleNamespace(step_index=9)]),
            {"failed_steps": [4, 2], "missing_step_end": [5]},
        )
        == 2
    )
