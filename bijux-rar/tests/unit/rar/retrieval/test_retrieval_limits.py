# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

import pytest

from bijux_rar.rar.retrieval.chunked_bm25 import ChunkedBM25Index
from bijux_rar.rar.retrieval.corpus import CorpusDoc, load_corpus_jsonl_stream


def test_load_corpus_respects_max_docs(tmp_path: Path) -> None:
    corpus = tmp_path / "c.jsonl"
    corpus.write_text(
        '\n'.join(
            [
                '{"doc_id":"d1","text":"a"}',
                '{"doc_id":"d2","text":"b"}',
                '{"doc_id":"d3","text":"c"}',
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        list(load_corpus_jsonl_stream(corpus, max_docs=2))


def test_build_index_respects_max_chunks(tmp_path: Path) -> None:
    docs = [
        CorpusDoc(doc_id="d1", text="alpha beta gamma", title=None, source=None),
        CorpusDoc(doc_id="d2", text="delta epsilon zeta", title=None, source=None),
    ]
    with pytest.raises(ValueError):
        ChunkedBM25Index.build(
            docs=docs,
            corpus_sha256="sha",
            chunk_chars=5,
            overlap_chars=1,
            max_chunks=1,
        )


def test_parallel_scoring_matches_serial(tmp_path: Path) -> None:
    docs = [
        CorpusDoc(doc_id="d1", text="hello world", title=None, source=None),
        CorpusDoc(doc_id="d2", text="hello there", title=None, source=None),
    ]
    idx = ChunkedBM25Index.build(
        docs=docs,
        corpus_sha256="sha",
        chunk_chars=50,
        overlap_chars=0,
    )
    serial = idx.top_k("hello", k=2, parallel=False)
    parallel = idx.top_k("hello", k=2, parallel=True)
    assert serial == parallel
