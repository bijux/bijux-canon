# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_rar.core.rar_types import ToolResult
from bijux_rar.rar.execution.tools import FrozenToolRegistry


def test_frozen_tool_registry_missing_call_raises() -> None:
    registry = FrozenToolRegistry(recorded={}, descriptors=[])
    try:
        registry.invoke(call=type("obj", (), {"id": "missing"}), seed=0)
    except KeyError as exc:
        assert "Missing recorded ToolResult" in str(exc)


def test_frozen_tool_registry_returns_recorded_results() -> None:
    result = ToolResult(call_id="c1", success=True, result={"ok": True})
    registry = FrozenToolRegistry(
        recorded={"c1": result}, descriptors=[]
    )
    out = registry.invoke(call=type("obj", (), {"id": "c1"}), seed=0)
    assert out == result
