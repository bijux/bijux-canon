# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

import pytest

from bijux_rar.rar.retrieval.corpus import load_corpus_jsonl, load_corpus_jsonl_stream
from bijux_rar.rar.retrieval.chunked_bm25 import build_or_load_index


def test_streaming_matches_full(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(
        '\n'.join(
            [
                '{"doc_id":"d1","text":"hello world"}',
                '{"doc_id":"d2","text":"another doc"}',
            ]
        ),
        encoding="utf-8",
    )
    streamed = list(load_corpus_jsonl_stream(corpus))
    full = load_corpus_jsonl(corpus)
    assert len(streamed) == len(full)
    assert [d.doc_id for d in streamed] == [d.doc_id for d in full]


def test_streaming_max_bytes_enforced(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text('{"doc_id":"d1","text":"hello world"}', encoding="utf-8")
    with pytest.raises(ValueError):
        list(load_corpus_jsonl_stream(corpus, max_bytes=5))


def test_build_or_load_respects_corpus_cap(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text('{"doc_id":"d1","text":"hello world"}', encoding="utf-8")
    with pytest.raises(ValueError):
        build_or_load_index(
            corpus_path=corpus,
            index_path=None,
            chunk_chars=10,
            overlap_chars=2,
            corpus_max_bytes=5,
        )
