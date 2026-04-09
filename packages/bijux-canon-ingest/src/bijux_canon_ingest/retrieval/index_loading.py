# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Persistence dispatch for retrieval index backends."""

from __future__ import annotations

import msgpack

from bijux_canon_ingest.retrieval.dense_index import NumpyCosineIndex
from bijux_canon_ingest.retrieval.lexical_index import BM25Index


def load_index(path: str) -> NumpyCosineIndex | BM25Index:
    """Load an index from disk."""

    with open(path, "rb") as handle:
        payload = msgpack.unpackb(handle.read(), raw=False)

    backend = payload.get("backend")
    if backend == "bm25":
        return BM25Index.load(path)
    if backend == "numpy-cosine":
        return NumpyCosineIndex.load(path)
    raise ValueError(f"unknown index backend: {backend}")


__all__ = ["load_index"]
