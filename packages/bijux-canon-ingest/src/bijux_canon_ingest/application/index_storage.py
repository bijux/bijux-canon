# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Persistence helpers for stored retrieval indexes."""

from __future__ import annotations

from pathlib import Path

from bijux_canon_ingest.application.index_runtime import IndexBackend, StoredIndex
from bijux_canon_ingest.result.types import Err, Ok, Result
from bijux_canon_ingest.retrieval.indexes import BM25Index, NumpyCosineIndex, load_index


def save_stored_index(index: StoredIndex, path: Path) -> Result[None, str]:
    """Persist a stored index to disk."""

    try:
        index.index.save(str(path))
        return Ok(None)
    except Exception as exc:  # pragma: no cover
        return Err(str(exc))


def load_stored_index(path: Path) -> Result[StoredIndex, str]:
    """Load a stored index from disk and wrap it with runtime metadata."""

    try:
        index = load_index(str(path))
        return Ok(wrap_loaded_index(index))
    except Exception as exc:  # pragma: no cover
        return Err(str(exc))


def wrap_loaded_index(index: BM25Index | NumpyCosineIndex) -> StoredIndex:
    """Attach runtime metadata to a loaded retrieval backend."""

    if isinstance(index, BM25Index):
        return StoredIndex(
            backend=IndexBackend.BM25,
            index=index,
            fingerprint=index.fingerprint,
        )
    if isinstance(index, NumpyCosineIndex):
        return StoredIndex(
            backend=IndexBackend.NUMPY_COSINE,
            index=index,
            fingerprint=index.fingerprint,
        )
    raise ValueError("unknown index backend")


__all__ = ["load_stored_index", "save_stored_index", "wrap_loaded_index"]
