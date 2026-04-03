# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""
BM25 retriever unit tests.

SPDX-FileCopyrightText: © 2025 Bijan Mousavi
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from pathlib import Path

from bijux_rar.rar.retrieval.bm25 import BM25Index
from bijux_rar.rar.retrieval.corpus import CorpusDoc
from bijux_rar.rar.retrieval.corpus import load_corpus_jsonl


def test_bm25_ranks_relevant_doc_first() -> None:
    corpus_path = (
        Path(__file__).resolve().parents[3] / "fixtures" / "corpus_small.jsonl"
    )
    docs = load_corpus_jsonl(corpus_path)
    idx = BM25Index.build(docs)

    ranked = idx.top_k("scripting language", k=2)
    assert ranked[0][0].doc_id == "d1"


def test_bm25_is_deterministic_when_all_scores_zero() -> None:
    corpus_path = (
        Path(__file__).resolve().parents[3] / "fixtures" / "corpus_small.jsonl"
    )
    docs = load_corpus_jsonl(corpus_path)
    idx = BM25Index.build(docs)

    ranked = idx.top_k("zzzzzz", k=3)
    assert [d.doc_id for d, _ in ranked] == ["d1", "d2", "d3"]


def test_bm25_tokenize_and_rounding() -> None:
    # Unicode tokens should be handled and score rounding should be stable
    docs = [
        CorpusDoc(doc_id="d1", text="naïve café", title=None, source=None),
        CorpusDoc(doc_id="d2", text="cafe naive", title=None, source=None),
    ]
    idx = BM25Index.build(docs)
    # identical terms after lowercasing/word detection
    ranked1 = idx.top_k("café naive", k=2, k1=1.2, b=0.75)
    ranked2 = idx.top_k("café naive", k=2, k1=1.2, b=0.75)
    # Deterministic ordering across repeated calls
    assert ranked1 == ranked2
    assert {d.doc_id for d, _ in ranked1} == {"d1", "d2"}
