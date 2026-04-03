# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Properties for the pure, deterministic stages used by the RAG pipeline."""

from __future__ import annotations

import hypothesis.strategies as st
from hypothesis import given

from bijux_rag import chunk_doc, clean_doc, embed_chunk, structural_dedup_chunks
from bijux_rag.core.rag_types import ChunkWithoutEmbedding, RagEnv, RawDoc
from tests.strategies import (
    doc_list_strategy,
    env_strategy,
    pipeline_chunk_strategy,
    raw_doc_strategy,
)


@given(doc=raw_doc_strategy())
def test_clean_doc_is_idempotent(doc: RawDoc) -> None:
    assert clean_doc(clean_doc(doc)) == clean_doc(doc)


@given(doc=raw_doc_strategy(), env=env_strategy())
def test_chunk_doc_partitions_text(doc: RawDoc, env: RagEnv) -> None:
    cleaned = clean_doc(doc)
    reconstructed = "".join(c.text for c in chunk_doc(cleaned, env))
    assert reconstructed == cleaned.abstract


@given(text=st.text(min_size=1))
def test_embed_chunk_depends_only_on_text(text: str) -> None:
    c1 = ChunkWithoutEmbedding(doc_id="a", text=text, start=0, end=len(text))
    c2 = ChunkWithoutEmbedding(doc_id="b", text=text, start=999, end=999 + len(text))
    assert embed_chunk(c1).embedding == embed_chunk(c2).embedding


@given(chunks=st.lists(pipeline_chunk_strategy()))
def test_structural_dedup_is_idempotent(chunks) -> None:
    once = structural_dedup_chunks(chunks)
    twice = structural_dedup_chunks(once)
    assert twice == once


@given(chunks=st.lists(pipeline_chunk_strategy()))
def test_structural_dedup_is_canonical_order(chunks) -> None:
    result = structural_dedup_chunks(chunks)
    expected = sorted(result, key=lambda c: (c.doc_id, c.start))
    assert result == expected


@given(docs=doc_list_strategy(), env=env_strategy())
def test_structural_dedup_after_pipeline_is_fixed_point(docs: list[RawDoc], env: RagEnv) -> None:
    cleaned = [clean_doc(d) for d in docs]
    embedded = [embed_chunk(c) for cd in cleaned for c in chunk_doc(cd, env)]
    chunks = structural_dedup_chunks(embedded)
    assert structural_dedup_chunks(chunks) == chunks
