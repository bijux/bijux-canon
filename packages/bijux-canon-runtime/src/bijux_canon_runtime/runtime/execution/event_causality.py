# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Execution event causality helpers."""

from __future__ import annotations

from bijux_canon_runtime.ontology import CausalityTag
from bijux_canon_runtime.ontology.public import EventType

_EVENT_CAUSALITY = {
    EventType.TOOL_CALL_START: CausalityTag.TOOL,
    EventType.TOOL_CALL_END: CausalityTag.TOOL,
    EventType.TOOL_CALL_FAIL: CausalityTag.TOOL,
    EventType.RETRIEVAL_START: CausalityTag.DATASET,
    EventType.RETRIEVAL_END: CausalityTag.DATASET,
    EventType.RETRIEVAL_FAILED: CausalityTag.DATASET,
    EventType.STEP_START: CausalityTag.AGENT,
    EventType.STEP_END: CausalityTag.AGENT,
    EventType.STEP_FAILED: CausalityTag.AGENT,
    EventType.VERIFICATION_START: CausalityTag.TOOL,
    EventType.VERIFICATION_PASS: CausalityTag.TOOL,
    EventType.VERIFICATION_FAIL: CausalityTag.TOOL,
    EventType.VERIFICATION_ESCALATE: CausalityTag.TOOL,
    EventType.VERIFICATION_ARBITRATION: CausalityTag.TOOL,
    EventType.HUMAN_INTERVENTION: CausalityTag.HUMAN,
    EventType.EXECUTION_INTERRUPTED: CausalityTag.ENVIRONMENT,
    EventType.SEMANTIC_VIOLATION: CausalityTag.ENVIRONMENT,
}


def event_causality_tag(event_type: EventType) -> CausalityTag:
    """Return the causality tag assigned to a runtime execution event."""
    return _EVENT_CAUSALITY.get(event_type, CausalityTag.AGENT)


__all__ = ["event_causality_tag"]
