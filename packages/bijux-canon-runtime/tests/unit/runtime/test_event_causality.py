# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from bijux_canon_runtime.ontology import CausalityTag
from bijux_canon_runtime.ontology.public import EventType
from bijux_canon_runtime.runtime.execution.event_causality import event_causality_tag
import pytest

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("event_type", "expected"),
    [
        (EventType.TOOL_CALL_FAIL, CausalityTag.TOOL),
        (EventType.RETRIEVAL_END, CausalityTag.DATASET),
        (EventType.STEP_FAILED, CausalityTag.AGENT),
        (EventType.VERIFICATION_ARBITRATION, CausalityTag.TOOL),
        (EventType.HUMAN_INTERVENTION, CausalityTag.HUMAN),
        (EventType.SEMANTIC_VIOLATION, CausalityTag.ENVIRONMENT),
    ],
)
def test_event_causality_tag_maps_runtime_events(
    event_type: EventType, expected: CausalityTag
) -> None:
    assert event_causality_tag(event_type) is expected
