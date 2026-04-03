# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Observability and debug types for ingest execution flows."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from bijux_canon_ingest.core.types import Chunk, CleanDoc, DocRule, RawDoc
from bijux_canon_ingest.streaming import TraceLens

TapDocs = Callable[[tuple[RawDoc, ...]], None]
TapCleaned = Callable[[tuple[CleanDoc, ...]], None]
TapChunks = Callable[[tuple[Chunk, ...]], None]
TapAny = Callable[[tuple[Any, ...]], None]


@dataclass(frozen=True)
class IngestTaps:
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
    """Boolean switches for tracing ingest stages."""

    trace_docs: bool = False
    trace_kept: bool = False
    trace_clean: bool = False
    trace_chunks: bool = False
    trace_embedded: bool = False
    probe_chunks: bool = False


@dataclass(frozen=True)
class Observations:
    """Deterministic summary for an ingest invocation."""

    total_docs: int
    total_chunks: int
    kept_docs: int | None = None
    cleaned_docs: int | None = None
    sample_doc_ids: tuple[str, ...] = ()
    sample_chunk_starts: tuple[int, ...] = ()
    extra: tuple[Any, ...] = ()
    warnings: tuple[Any, ...] = ()


@dataclass
class IngestTrace:
    """Bounded trace samples for each ingest stage."""

    docs: TraceLens[RawDoc] = field(default_factory=TraceLens)
    cleaned: TraceLens[CleanDoc] = field(default_factory=TraceLens)
    chunks: TraceLens[Any] = field(
        default_factory=TraceLens
    )  # typically ChunkWithoutEmbedding
    embedded: TraceLens[Any] = field(default_factory=TraceLens)  # typically Chunk


__all__ = [
    "DocRule",
    "IngestTaps",
    "DebugConfig",
    "Observations",
    "TraceLens",
    "IngestTrace",
]
