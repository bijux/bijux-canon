# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

import pytest

from bijux_rar.rar.retrieval.corpus import load_corpus_jsonl, load_corpus_jsonl_stream


def test_load_corpus_jsonl_roundtrip(tmp_path: Path) -> None:
    corpus = tmp_path / "c.jsonl"
    corpus.write_text('{"doc_id":"d1","text":"hello"}\n', encoding="utf-8")
    docs = load_corpus_jsonl(corpus)
    assert docs[0].doc_id == "d1"
    assert docs[0].text == "hello"


def test_load_corpus_stream_validates_json(tmp_path: Path) -> None:
    corpus = tmp_path / "c.jsonl"
    corpus.write_text("not-json", encoding="utf-8")
    with pytest.raises(ValueError):
        list(load_corpus_jsonl_stream(corpus))
