# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from bijux_canon_reason.core.types import ToolCall
from bijux_canon_reason.execution.runtime import Runtime
from bijux_canon_reason.retrieval.chunked_bm25 import build_or_load_index


def test_local_bm25_descriptor_and_provenance(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(
        '{"doc_id":"d1","text":"alpha beta"}\n{"doc_id":"d2","text":"beta gamma"}',
        encoding="utf-8",
    )

    rt = Runtime.local_bm25(
        seed=7,
        corpus_path=corpus,
        artifacts_dir=tmp_path,
        chunk_chars=6,
        overlap_chars=2,
        k1=1.1,
        b=0.6,
    )

    desc = rt.descriptor
    assert desc.kind == "LocalBM25Runtime"
    retrieve_tool = {t.name: t for t in desc.tools}["retrieve"]

    # fingerprint must change when chunk parameters change
    rt_diff = Runtime.local_bm25(
        seed=7,
        corpus_path=corpus,
        artifacts_dir=tmp_path,
        chunk_chars=4,  # different from 6
        overlap_chars=1,
        k1=1.1,
        b=0.6,
    )
    retrieve_tool_diff = {t.name: t for t in rt_diff.descriptor.tools}["retrieve"]
    assert retrieve_tool.config_fingerprint != retrieve_tool_diff.config_fingerprint

    # ensure index builds and fingerprints match config params
    idx, corpus_sha, index_sha = build_or_load_index(
        corpus_path=corpus,
        index_path=tmp_path / "provenance" / "index.json",
        chunk_chars=6,
        overlap_chars=2,
    )
    assert idx.corpus_sha256 == corpus_sha
    assert index_sha

    result = rt.tools.invoke(
        ToolCall(
            id="call-1",
            tool_name="retrieve",
            arguments={"query": "beta", "top_k": 1},
            step_id="gather-1",
            call_idx=0,
        ),
        seed=rt.seed,
    )
    assert result.success is True
    provenance_dir = tmp_path / "provenance"
    assert (provenance_dir / "retrieval_provenance.json").exists()
    assert (provenance_dir / "chunks.jsonl").exists()
