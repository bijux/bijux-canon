# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from bijux_rar.rar.retrieval.chunked_bm25 import build_or_load_index


def _write_corpus(path: Path) -> None:
    path.write_text(
        '\n'.join(
            [
                '{"doc_id": "d1", "text": "alpha beta gamma"}',
                '{"doc_id": "d2", "text": "beta gamma delta"}',
            ]
        ),
        encoding="utf-8",
    )


def test_chunked_bm25_persist_and_reload(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.jsonl"
    _write_corpus(corpus)

    index_path = tmp_path / "idx" / "bm25.json"
    idx1, corpus_sha1, index_sha1 = build_or_load_index(
        corpus_path=corpus,
        index_path=index_path,
        chunk_chars=8,
        overlap_chars=2,
    )

    # reload from disk should reuse hash and rankings
    idx2, corpus_sha2, index_sha2 = build_or_load_index(
        corpus_path=corpus,
        index_path=index_path,
        chunk_chars=8,
        overlap_chars=2,
    )

    assert corpus_sha1 == corpus_sha2
    assert index_sha1 == index_sha2

    ranked1 = idx1.top_k("alpha", k=1)
    ranked2 = idx2.top_k("alpha", k=1)
    assert ranked1[0][0].chunk_id == ranked2[0][0].chunk_id


def test_chunked_bm25_rebuilds_on_corpus_change(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.jsonl"
    _write_corpus(corpus)
    index_path = tmp_path / "idx.json"

    _, _, index_sha1 = build_or_load_index(
        corpus_path=corpus,
        index_path=index_path,
        chunk_chars=12,
        overlap_chars=4,
    )

    # mutate corpus -> hash must change, index must rebuild
    corpus.write_text(
        corpus.read_text(encoding="utf-8") + '\n{"doc_id": "d3", "text": "alpha alpha"}',
        encoding="utf-8",
    )

    _, _, index_sha2 = build_or_load_index(
        corpus_path=corpus,
        index_path=index_path,
        chunk_chars=12,
        overlap_chars=4,
    )
    assert index_sha1 != index_sha2
