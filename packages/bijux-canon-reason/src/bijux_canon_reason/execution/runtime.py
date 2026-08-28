# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Runtime helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from bijux_canon_reason.core.types import (
    RuntimeDescriptor,
    ToolCall,
    ToolDescriptor,
    ToolResult,
)
from bijux_canon_reason.execution.tool_runtime import (
    BM25Retriever,
    FrozenToolRegistry,
    ToolRegistry,
)

RuntimeMode = Literal["live", "frozen"]


class ToolExecutor(Protocol):
    """Represents tool executor."""

    def describe(self) -> list[ToolDescriptor]:
        """Describe the available tools."""

        ...

    def invoke(self, call: ToolCall, *, seed: int) -> ToolResult:
        """Invoke a tool call."""

        ...


class ExecutionRuntime(Protocol):
    """Represents execution runtime."""

    @property
    def seed(self) -> int: ...

    @property
    def tools(self) -> ToolExecutor: ...

    @property
    def runtime_kind(self) -> str: ...

    @property
    def mode(self) -> RuntimeMode: ...

    @property
    def artifacts_dir(self) -> Path | None: ...

    @property
    def descriptor(self) -> RuntimeDescriptor:
        """Return the runtime descriptor."""

        ...


@dataclass(frozen=True)
class Runtime:
    """Represents runtime."""

    seed: int
    tools: ToolRegistry | FrozenToolRegistry
    runtime_kind: str
    mode: RuntimeMode
    artifacts_dir: Path | None

    @property
    def descriptor(self) -> RuntimeDescriptor:
        """Return the descriptor payload."""
        if isinstance(self.tools, FrozenToolRegistry):
            return RuntimeDescriptor(
                kind=self.runtime_kind, mode=self.mode, tools=self.tools.describe()
            )
        return RuntimeDescriptor(
            kind=self.runtime_kind,
            mode=self.mode,
            tools=self.tools.describe(),
        )

    @staticmethod
    def credential_free(seed: int, *, artifacts_dir: Path | None = None) -> Runtime:
        """Create an honest no-tool runtime for evidence-free local operation."""
        return Runtime(
            seed=seed,
            tools=ToolRegistry(tools={}),
            runtime_kind="CredentialFreeRuntime",
            mode="live",
            artifacts_dir=artifacts_dir,
        )

    @staticmethod
    def local_bm25(
        *,
        seed: int,
        corpus_path: Path,
        artifacts_dir: Path | None = None,
        chunk_chars: int = 800,
        overlap_chars: int = 120,
        k1: float = 1.2,
        b: float = 0.75,
        corpus_max_bytes: int | None = None,
    ) -> Runtime:
        """Runtime with a deterministic local BM25 retriever."""
        tools = ToolRegistry(
            tools={
                "retrieve": BM25Retriever(
                    corpus_path=corpus_path,
                    artifacts_dir=artifacts_dir,
                    chunk_chars=chunk_chars,
                    overlap_chars=overlap_chars,
                    k1=k1,
                    b=b,
                    corpus_max_bytes=corpus_max_bytes,
                ),
            }
        )
        return Runtime(
            seed=seed,
            tools=tools,
            runtime_kind="LocalBM25Runtime",
            mode="live",
            artifacts_dir=artifacts_dir,
        )

    @staticmethod
    def frozen(
        *,
        seed: int,
        recorded_results: Mapping[str, ToolResult],
        artifacts_dir: Path | None = None,
        descriptors: list[ToolDescriptor] | None = None,
        mode: RuntimeMode = "frozen",
        runtime_kind: str = "ReplayRuntime",
    ) -> Runtime:
        """Handle frozen."""
        frozen_tools = FrozenToolRegistry(
            recorded=dict(recorded_results),
            descriptors=list(descriptors or []),
        )
        return Runtime(
            seed=seed,
            tools=frozen_tools,
            runtime_kind=runtime_kind,
            mode=mode,
            artifacts_dir=artifacts_dir,
        )
