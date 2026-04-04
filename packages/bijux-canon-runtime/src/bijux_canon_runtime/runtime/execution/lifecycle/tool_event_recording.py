# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tool invocation recording helpers for step execution."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from bijux_canon_runtime.model.identifiers.tool_invocation import ToolInvocation
from bijux_canon_runtime.observability.classification.fingerprint import (
    fingerprint_inputs,
)
from bijux_canon_runtime.ontology import DeterminismLevel
from bijux_canon_runtime.ontology.ids import ContentHash, ToolID
from bijux_canon_runtime.ontology.public import EventType


class ToolEventCallbacks(Protocol):
    """Callback contract required for tool-event recording."""

    def record_tool_invocation(self, invocation: ToolInvocation) -> None:
        """Record a tool invocation."""
        ...

    def record_event(
        self, event_type: EventType, step_index: int, payload: dict[str, object]
    ) -> None:
        """Record a runtime event."""
        ...


def record_tool_success(
    *,
    step_index: int,
    tool_id: ToolID,
    determinism_level: DeterminismLevel,
    tool_input: Mapping[str, object],
    output_fingerprint: str,
    pending_invocations: dict[tuple[int, ToolID], ContentHash],
    callbacks: ToolEventCallbacks,
) -> None:
    """Record a successful tool invocation and its closing event."""
    input_fingerprint = pending_invocations.pop(
        (step_index, tool_id),
        ContentHash(fingerprint_inputs(tool_input)),
    )
    callbacks.record_tool_invocation(
        ToolInvocation(
            spec_version="v1",
            tool_id=tool_id,
            determinism_level=determinism_level,
            inputs_fingerprint=input_fingerprint,
            outputs_fingerprint=ContentHash(output_fingerprint),
            duration=0.0,
            outcome="success",
        )
    )
    callbacks.record_event(
        EventType.TOOL_CALL_END,
        step_index,
        {
            "tool_id": tool_id,
            "input_fingerprint": fingerprint_inputs(tool_input),
            "output_fingerprint": output_fingerprint,
        },
    )


def record_tool_failure(
    *,
    step_index: int,
    tool_id: ToolID,
    determinism_level: DeterminismLevel,
    tool_input: Mapping[str, object],
    pending_invocations: dict[tuple[int, ToolID], ContentHash],
    callbacks: ToolEventCallbacks,
    error: Exception,
    failure_event: EventType,
    failure_payload: dict[str, object],
) -> None:
    """Record a failed tool invocation and the terminal failure event."""
    input_fingerprint = pending_invocations.pop(
        (step_index, tool_id),
        ContentHash(fingerprint_inputs(tool_input)),
    )
    callbacks.record_tool_invocation(
        ToolInvocation(
            spec_version="v1",
            tool_id=tool_id,
            determinism_level=determinism_level,
            inputs_fingerprint=input_fingerprint,
            outputs_fingerprint=None,
            duration=0.0,
            outcome="fail",
        )
    )
    callbacks.record_event(
        EventType.TOOL_CALL_FAIL,
        step_index,
        {
            "tool_id": tool_id,
            "input_fingerprint": fingerprint_inputs(tool_input),
            "error": str(error),
        },
    )
    callbacks.record_event(failure_event, step_index, failure_payload)


__all__ = ["record_tool_failure", "record_tool_success"]
