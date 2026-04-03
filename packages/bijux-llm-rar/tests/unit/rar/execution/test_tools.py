# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from bijux_rar.rar.execution.tools import BM25Retriever, FakeTool


def test_fake_tool_retrieve_returns_evidences() -> None:
    tool = FakeTool(name="retrieve")
    out = tool.invoke(arguments={"query": "q", "top_k": 2}, seed=0)
    assert isinstance(out, dict)
    assert "evidences" in out
    assert len(out["evidences"]) == 2


def test_bm25_retriever_config_fingerprint_changes_with_params(tmp_path: Path) -> None:
    corpus = tmp_path / "c.jsonl"
    corpus.write_text('{"doc_id":"d1","text":"a b"}', encoding="utf-8")
    r1 = BM25Retriever(corpus_path=corpus, chunk_chars=8, overlap_chars=2)
    r2 = BM25Retriever(corpus_path=corpus, chunk_chars=4, overlap_chars=1)
    assert r1.config_fingerprint != r2.config_fingerprint
