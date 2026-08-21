# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from bijux_canon_reason.execution.runtime import Runtime
from bijux_canon_reason.execution.tool_runtime import BM25Retriever


def test_credential_free_runtime_exposes_no_synthetic_tools() -> None:
    runtime = Runtime.credential_free(seed=0)

    assert runtime.tools.describe() == []
    assert runtime.descriptor.kind == "CredentialFreeRuntime"


def test_bm25_retriever_config_fingerprint_changes_with_params(tmp_path: Path) -> None:
    corpus = tmp_path / "c.jsonl"
    corpus.write_text('{"doc_id":"d1","text":"a b"}', encoding="utf-8")
    r1 = BM25Retriever(corpus_path=corpus, chunk_chars=8, overlap_chars=2)
    r2 = BM25Retriever(corpus_path=corpus, chunk_chars=4, overlap_chars=1)
    assert r1.config_fingerprint != r2.config_fingerprint
