# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from bijux_rar.core.rar_types import RuntimeDescriptor, ToolDescriptor, ToolResult
from bijux_rar.rar.execution.tools import (
    BM25Retriever,
    FakeTool,
    FrozenToolRegistry,
    ToolRegistry,
)


@dataclass(frozen=True)
class Runtime:
    seed: int
    tools: ToolRegistry | FrozenToolRegistry
    runtime_kind: str
    mode: Literal["live", "frozen"]
    artifacts_dir: Path | None

    @property
    def descriptor(self) -> RuntimeDescriptor:
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
    def fake(seed: int, *, artifacts_dir: Path | None = None) -> Runtime:
        tools = ToolRegistry(
            tools={
                "retrieve": FakeTool(name="retrieve"),
                "compute": FakeTool(name="compute"),
            }
        )
        return Runtime(
            seed=seed,
            tools=tools,
            runtime_kind="FakeRuntime",
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
                "compute": FakeTool(name="compute"),
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
        mode: Literal["live", "frozen"] = "frozen",
        runtime_kind: str = "FrozenRuntime",
    ) -> Runtime:
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
