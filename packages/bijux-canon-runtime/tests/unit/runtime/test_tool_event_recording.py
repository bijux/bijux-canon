from __future__ import annotations

from bijux_canon_runtime.model.identifiers.tool_invocation import ToolInvocation
from bijux_canon_runtime.ontology import DeterminismLevel
from bijux_canon_runtime.ontology.ids import ContentHash, ToolID
from bijux_canon_runtime.ontology.public import EventType
from bijux_canon_runtime.runtime.execution.lifecycle.step_operations import (
    StepCallbacks,
)
from bijux_canon_runtime.runtime.execution.lifecycle.tool_event_recording import (
    record_tool_failure,
    record_tool_success,
)


def test_record_tool_success_records_invocation_and_end_event() -> None:
    events: list[tuple[EventType, int, dict[str, object]]] = []
    invocations: list[ToolInvocation] = []
    callbacks = StepCallbacks(
        record_event=lambda event_type, step_index, payload: events.append(
            (event_type, step_index, payload)
        ),
        record_tool_invocation=invocations.append,
        record_evidence=lambda _items: None,
        record_artifacts=lambda _items: None,
        record_claims=lambda _claims: None,
        flush_entropy_usage=lambda: None,
        enforce_entropy_authorization=lambda: None,
        save_checkpoint=lambda _step_index: None,
    )

    record_tool_success(
        step_index=2,
        tool_id=ToolID("tool"),
        determinism_level=DeterminismLevel.STRICT,
        tool_input={"tool_id": "tool", "value": "input"},
        output_fingerprint="output",
        pending_invocations={(2, ToolID("tool")): ContentHash("input")},
        callbacks=callbacks,
    )

    assert [invocation.outcome for invocation in invocations] == ["success"]
    assert events[0][0] is EventType.TOOL_CALL_END


def test_record_tool_failure_records_invocation_and_failure_events() -> None:
    events: list[tuple[EventType, int, dict[str, object]]] = []
    invocations: list[ToolInvocation] = []
    callbacks = StepCallbacks(
        record_event=lambda event_type, step_index, payload: events.append(
            (event_type, step_index, payload)
        ),
        record_tool_invocation=invocations.append,
        record_evidence=lambda _items: None,
        record_artifacts=lambda _items: None,
        record_claims=lambda _claims: None,
        flush_entropy_usage=lambda: None,
        enforce_entropy_authorization=lambda: None,
        save_checkpoint=lambda _step_index: None,
    )

    record_tool_failure(
        step_index=4,
        tool_id=ToolID("tool"),
        determinism_level=DeterminismLevel.BOUNDED,
        tool_input={"tool_id": "tool", "value": "input"},
        pending_invocations={(4, ToolID("tool")): ContentHash("input")},
        callbacks=callbacks,
        error=RuntimeError("boom"),
        failure_event=EventType.STEP_FAILED,
        failure_payload={"step_index": 4, "error": "boom"},
    )

    assert [invocation.outcome for invocation in invocations] == ["fail"]
    assert [event_type for event_type, _, _ in events] == [
        EventType.TOOL_CALL_FAIL,
        EventType.STEP_FAILED,
    ]
