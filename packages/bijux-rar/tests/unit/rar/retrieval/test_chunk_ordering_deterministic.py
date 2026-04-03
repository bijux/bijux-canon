# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_rar.rar.retrieval.chunked_bm25 import ChunkedBM25Index
from bijux_rar.rar.retrieval.corpus import CorpusDoc


def test_chunks_sorted_by_doc_and_span() -> None:
    docs = [
        CorpusDoc(doc_id="b", text="hello world", title=None, source=None),
        CorpusDoc(doc_id="a", text="hello world again", title=None, source=None),
    ]
    idx = ChunkedBM25Index.build(
        docs=docs,
        corpus_sha256="sha",
        chunk_chars=5,
        overlap_chars=0,
        max_chunks=None,
    )
    # ordering must be by doc_id then start_byte
    doc_ids = [c.doc_id for c in idx.chunks]
    assert doc_ids == sorted(doc_ids)
