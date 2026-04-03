# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Public retrieval index facade.

Callers keep importing from ``bijux_canon_ingest.retrieval.indexes`` while the
implementations live in dedicated modules for dense retrieval, lexical
retrieval, shared math, and build/load entrypoints.
"""

from __future__ import annotations

from bijux_canon_ingest.retrieval._index_common import SCHEMA_VERSION
from bijux_canon_ingest.retrieval.dense_index import NumpyCosineIndex
from bijux_canon_ingest.retrieval.index_builders import (
    build_bm25_index,
    build_numpy_cosine_index,
    load_index,
)
from bijux_canon_ingest.retrieval.lexical_index import BM25Index
from bijux_canon_ingest.retrieval.text_analysis import (
    stable_token_bucket as _stable_token_bucket,
)
from bijux_canon_ingest.retrieval.text_analysis import tokenize as _tokenize

__all__ = [
    "BM25Index",
    "NumpyCosineIndex",
    "SCHEMA_VERSION",
    "build_bm25_index",
    "build_numpy_cosine_index",
    "load_index",
]
