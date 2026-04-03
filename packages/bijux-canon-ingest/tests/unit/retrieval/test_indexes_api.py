# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from bijux_canon_ingest.retrieval import indexes
from bijux_canon_ingest.retrieval._index_common import SCHEMA_VERSION
from bijux_canon_ingest.retrieval.dense_index import NumpyCosineIndex
from bijux_canon_ingest.retrieval.index_builders import (
    build_bm25_index,
    build_numpy_cosine_index,
    load_index,
)
from bijux_canon_ingest.retrieval.lexical_index import BM25Index


def test_indexes_facade_re_exports_public_constructors() -> None:
    assert indexes.BM25Index is BM25Index
    assert indexes.NumpyCosineIndex is NumpyCosineIndex
    assert indexes.build_bm25_index is build_bm25_index
    assert indexes.build_numpy_cosine_index is build_numpy_cosine_index
    assert indexes.load_index is load_index


def test_indexes_facade_exports_schema_version() -> None:
    assert indexes.SCHEMA_VERSION == SCHEMA_VERSION
    assert "SCHEMA_VERSION" in indexes.__all__
