# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Public API types for the RAG surface (end-of-Bijux RAG).

Most of these types are introduced in Bijux RAG and extended in Bijux RAG
(notably tracing/stream observability).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from bijux_rag.core.rag_types import Chunk, CleanDoc, DocRule, RawDoc
from bijux_rag.streaming import TraceLens

TapDocs = Callable[[tuple[RawDoc, ...]], None]
TapCleaned = Callable[[tuple[CleanDoc, ...]], None]
TapChunks = Callable[[tuple[Chunk, ...]], None]
TapAny = Callable[[tuple[Any, ...]], None]


@dataclass(frozen=True)
class RagTaps:
    """Observation-only hooks for intermediate values.

    Tap handlers must be observational only: they may log or collect metrics,
    but must not mutate inputs or influence returned values.
    """

    docs: TapDocs | None = None
    cleaned: TapCleaned | None = None
    chunks: TapChunks | None = None
    extra: Mapping[str, TapAny] = field(default_factory=dict)


@dataclass(frozen=True)
class DebugConfig:
    trace_docs: bool = False
    trace_kept: bool = False
    trace_clean: bool = False
    trace_chunks: bool = False
    trace_embedded: bool = False
    probe_chunks: bool = False


@dataclass(frozen=True)
class Observations:
    """Deterministic summary for a RAG invocation (end-of-Bijux RAG)."""

    total_docs: int
    total_chunks: int
    kept_docs: int | None = None
    cleaned_docs: int | None = None
    sample_doc_ids: tuple[str, ...] = ()
    sample_chunk_starts: tuple[int, ...] = ()
    extra: tuple[Any, ...] = ()
    warnings: tuple[Any, ...] = ()


@dataclass
class RagTraceV3:
    """Bijux RAG stream trace: bounded samples for each pipeline stage."""

    docs: TraceLens[RawDoc] = field(default_factory=TraceLens)
    cleaned: TraceLens[CleanDoc] = field(default_factory=TraceLens)
    chunks: TraceLens[Any] = field(default_factory=TraceLens)  # typically ChunkWithoutEmbedding
    embedded: TraceLens[Any] = field(default_factory=TraceLens)  # typically Chunk


__all__ = ["DocRule", "RagTaps", "DebugConfig", "Observations", "TraceLens", "RagTraceV3"]
