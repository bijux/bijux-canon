# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from dataclasses import replace

from hypothesis import given
from hypothesis import strategies as st

from bijux_rag.fp.error import ErrorCode
from bijux_rag.fp.validation import VFailure, VSuccess
from bijux_rag.rag.domain import ChunkMetadata, ChunkText, Embedding, assemble

raw_tags = st.lists(st.text(min_size=1), min_size=0, max_size=15)


@given(
    content=st.text(min_size=1),
    source=st.text(),
    raw_tags=raw_tags,
    model=st.none() | st.text(),
    dim=st.none() | st.integers(min_value=1, max_value=8192),
    vector=st.none()
    | st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=1, max_size=10),
)
def test_assemble_success_and_dedup(content, source, raw_tags, model, dim, vector) -> None:
    meta = ChunkMetadata(
        source=source, tags=tuple(raw_tags), embedding_model=model, expected_dim=dim
    )
    emb = Embedding(vector=tuple(vector or ()), model=model or "test") if vector else None

    if emb:
        meta = replace(meta, expected_dim=emb.dim, embedding_model=emb.model)

    v = assemble(ChunkText(content=content), meta, emb)
    assert isinstance(v, VSuccess)
    chunk = v.value

    assert chunk.text.content == content
    assert chunk.metadata.source == source
    assert chunk.metadata.embedding_model == (emb.model if emb else model)
    assert chunk.metadata.expected_dim == (emb.dim if emb else dim)

    if emb is not None:
        assert chunk.embedding is not None
        assert chunk.embedding.vector == emb.vector
        assert chunk.embedding.model == emb.model
        assert chunk.embedding.dim == emb.dim
    else:
        assert chunk.embedding is None

    expected_tags = tuple(dict.fromkeys(raw_tags))
    assert chunk.metadata.tags == expected_tags


@given(
    content=st.text(min_size=1),
    source=st.text(),
    tags=st.lists(st.text(), min_size=1, max_size=10),
    model=st.text(min_size=1),
    vector=st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=1, max_size=10),
)
def test_assemble_model_mismatch_fails(content, source, tags, model, vector) -> None:
    meta = ChunkMetadata(source=source, tags=tuple(tags), embedding_model=model + "-wrong")
    emb = Embedding(vector=tuple(vector), model=model)
    v = assemble(ChunkText(content=content), meta, emb)
    assert isinstance(v, VFailure)
    assert any(e.code == ErrorCode.EMB_MODEL_MISMATCH for e in v.errors)


@given(
    content=st.text(min_size=1),
    source=st.text(),
    tags=st.lists(st.text(), min_size=1, max_size=10),
    model=st.text(min_size=1),
    vector=st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=1, max_size=10),
)
def test_assemble_dim_mismatch_fails(content, source, tags, model, vector) -> None:
    meta = ChunkMetadata(
        source=source, tags=tuple(tags), embedding_model=model, expected_dim=len(vector) + 1
    )
    emb = Embedding(vector=tuple(vector), model=model)
    v = assemble(ChunkText(content=content), meta, emb)
    assert isinstance(v, VFailure)
    assert any(e.code == ErrorCode.EMB_DIM_MISMATCH for e in v.errors)
