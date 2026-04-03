# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from bijux_rag.core.rag_types import RagEnv, RawDoc
from bijux_rag.rag.stdlib_fp import rag_iter_stdlib


def test_rag_iter_stdlib_smoke() -> None:
    env = RagEnv(chunk_size=4, overlap=0, tail_policy="emit_short")
    docs = [
        RawDoc(doc_id="d1", title="t", abstract="hello", categories="cs.AI"),
    ]
    out = list(rag_iter_stdlib(docs, env))
    assert out
    assert out[0].doc_id == "d1"
