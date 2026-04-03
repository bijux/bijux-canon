# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_rar.core.rar_types import RuntimeDescriptor, ToolCall, ToolDescriptor, ToolResult
from bijux_rar.rar.execution.frozen_runtime import FrozenRuntime, RecordedCall


def test_frozen_runtime_descriptor_override() -> None:
    desc = RuntimeDescriptor(kind="FrozenRuntime", mode="frozen", tools=[ToolDescriptor(name="x", version="1", config_fingerprint="cfg")])
    fr = FrozenRuntime(recordings={}, seed=0, descriptor_override=desc)
    assert fr.descriptor == desc


def test_frozen_runtime_missing_recording_returns_failure() -> None:
    call = ToolCall(id="c1", tool_name="t", arguments={}, step_id="s", call_idx=0)
    fr = FrozenRuntime(recordings={}, seed=0)
    result = fr.tools.invoke(call, seed=0)
    assert result.success is False
    assert "no recorded result" in (result.error or "")


def test_frozen_runtime_returns_recorded_result() -> None:
    call = ToolCall(id="c1", tool_name="t", arguments={}, step_id="s", call_idx=0)
    recorded = RecordedCall(call_id="c1", result=ToolResult(call_id="c1", success=True, result={"ok": True}))
    fr = FrozenRuntime(recordings={"c1": recorded}, seed=0)
    result = fr.tools.invoke(call, seed=0)
    assert result.success is True
    assert result.result == {"ok": True}
