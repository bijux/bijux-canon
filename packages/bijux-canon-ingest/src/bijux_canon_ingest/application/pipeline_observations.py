# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Observation helpers for materialized ingest pipeline runs."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

from bijux_canon_ingest.core.types import Chunk, CleanDoc, RawDoc
from bijux_canon_ingest.observability import Observations

T = TypeVar("T")


def tap_items(
    items: Sequence[T], handler: Callable[[tuple[T, ...]], None] | None
) -> Sequence[T]:
    """Pass through materialized values while notifying an optional observer."""

    if handler is not None:
        handler(tuple(items))
    return items


def build_observations(
    *,
    docs: Sequence[RawDoc],
    kept_docs: Sequence[RawDoc],
    cleaned_docs: Sequence[CleanDoc],
    chunks: Sequence[Chunk],
    sample_size: int,
) -> Observations:
    """Construct the deterministic observation summary for a pipeline run."""

    return Observations(
        total_docs=len(docs),
        kept_docs=len(kept_docs),
        cleaned_docs=len(cleaned_docs),
        total_chunks=len(chunks),
        sample_doc_ids=tuple(doc.doc_id for doc in kept_docs[:sample_size]),
        sample_chunk_starts=tuple(chunk.start for chunk in chunks[:sample_size]),
        extra=(),
        warnings=(),
    )


__all__ = ["build_observations", "tap_items"]
