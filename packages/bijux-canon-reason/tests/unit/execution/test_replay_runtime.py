# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_canon_reason.core.types import ToolCall, ToolResult
from bijux_canon_reason.execution.tool_runtime import FrozenToolRegistry


def test_frozen_tool_registry_missing_call_raises() -> None:
    registry = FrozenToolRegistry(recorded={}, descriptors=[])
    try:
        registry.invoke(
            call=ToolCall(
                id="missing",
                tool_name="compute",
                arguments={},
                step_id="s1",
                call_idx=0,
            ),
            seed=0,
        )
    except KeyError as exc:
        assert "Missing recorded ToolResult" in str(exc)


def test_frozen_tool_registry_returns_recorded_results() -> None:
    result = ToolResult(call_id="c1", success=True, result={"ok": True})
    registry = FrozenToolRegistry(recorded={"c1": result}, descriptors=[])
    out = registry.invoke(
        call=ToolCall(
            id="c1",
            tool_name="compute",
            arguments={},
            step_id="s1",
            call_idx=0,
        ),
        seed=0,
    )
    assert out == result
