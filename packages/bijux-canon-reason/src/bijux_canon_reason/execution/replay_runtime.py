# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Replay runtime helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from bijux_canon_reason.core.types import (
    RuntimeDescriptor,
    ToolCall,
    ToolDescriptor,
    ToolResult,
)


@dataclass(frozen=True)
class RecordedCall:
    """Represents recorded call."""

    call_id: str
    result: ToolResult


class ReplayToolRegistry:
    """Represents replay tool registry."""

    def __init__(self, recordings: Mapping[str, RecordedCall]):
        """Initialize the instance."""
        self.recordings = recordings

    def invoke(self, call: ToolCall, *, seed: int) -> ToolResult:
        """Invoke the requested operation."""
        recorded = self.recordings.get(call.id)
        if recorded is None:
            return ToolResult(
                call_id=call.id, success=False, result=None, error="no recorded result"
            )
        return recorded.result


@dataclass(frozen=True)
class ReplayRuntime:
    """Represents replay runtime."""

    recordings: Mapping[str, RecordedCall]
    seed: int
    runtime_kind: str = "ReplayRuntime"
    descriptor_override: RuntimeDescriptor | None = None

    @property
    def tools(self) -> ReplayToolRegistry:
        """Handle tools."""
        return ReplayToolRegistry(self.recordings)

    @property
    def descriptor(self) -> RuntimeDescriptor:
        """Return the descriptor payload."""
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
