# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

from bijux_rag.core.rag_types import RawDoc
from bijux_rag.rag.app import RagApp
from bijux_rag.result import is_ok


def test_real_rag_smoke_build_retrieve_ask(tmp_path: Path) -> None:
    app = RagApp()
    docs = [
        RawDoc(
            doc_id="d1",
            title="Mito",
            abstract="Mitochondria are the powerhouse of the cell.",
            categories="bio",
        ),
        RawDoc(
            doc_id="d2",
            title="Chloro",
            abstract="Chloroplasts perform photosynthesis in plants.",
            categories="bio",
        ),
    ]
    build = app.build_index(docs=docs, backend="bm25", chunk_size=64, overlap=0)
    assert is_ok(build)
    idx = build.value
    p = tmp_path / "idx.msgpack"
    saved = app.save_index(idx, p)
    assert is_ok(saved)
    loaded = app.load_index(p)
    assert is_ok(loaded)
    idx_loaded = loaded.value
    r = app.retrieve(index=idx_loaded, query="powerhouse of the cell", top_k=3, filters={})
    assert is_ok(r)
    got = [c.chunk.doc_id for c in r.value]
    assert got and got[0] == "d1"
    a = app.ask(
        index=idx_loaded,
        query="What is the powerhouse of the cell?",
        top_k=3,
        filters={},
        rerank=True,
    )
    assert is_ok(a)
    ans = a.value
    citations = ans["citations"]
    assert citations, "non-trivial answer must include citations"
    assert citations[0]["doc_id"] == "d1"
