# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from bijux_rar.core.rar_types import (
    RuntimeDescriptor,
    ToolCall,
    ToolDescriptor,
    ToolResult,
)


@dataclass(frozen=True)
class RecordedCall:
    call_id: str
    result: ToolResult


class FrozenToolRegistry:
    def __init__(self, recordings: Mapping[str, RecordedCall]):
        self.recordings = recordings

    def invoke(self, call: ToolCall, *, seed: int) -> ToolResult:
        recorded = self.recordings.get(call.id)
        if recorded is None:
            return ToolResult(
                call_id=call.id, success=False, result=None, error="no recorded result"
            )
        return recorded.result


@dataclass(frozen=True)
class FrozenRuntime:
    recordings: Mapping[str, RecordedCall]
    seed: int
    runtime_kind: str = "FrozenRuntime"
    descriptor_override: RuntimeDescriptor | None = None

    @property
    def tools(self) -> FrozenToolRegistry:
        return FrozenToolRegistry(self.recordings)

    @property
    def descriptor(self) -> RuntimeDescriptor:
        if self.descriptor_override is not None:
            return self.descriptor_override
        return RuntimeDescriptor(
            kind=self.runtime_kind,
            mode="frozen",
            tools=[
                ToolDescriptor(
                    name="frozen", version="0.0.0", config_fingerprint="frozen"
                )
            ],
        )
