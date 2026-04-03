# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Shared Hypothesis strategies used across the test suite."""

from __future__ import annotations

import hashlib

import hypothesis.strategies as st
from hypothesis.strategies import SearchStrategy

from bijux_rag.core.rag_types import Chunk, RagEnv, RawDoc, TextNode, TreeDoc


def raw_doc_strategy() -> SearchStrategy[RawDoc]:
    """Strategy producing RawDoc instances with realistic text fields."""
    return st.builds(
        RawDoc,
        doc_id=st.text(
            min_size=1,
            max_size=20,
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_",
        ),
        title=st.text(max_size=100),
        abstract=st.text(max_size=2000),
        categories=st.text(max_size=50),
    )


def doc_list_strategy() -> SearchStrategy[list[RawDoc]]:
    """Strategy emitting small batches of RawDoc inputs."""
    return st.lists(raw_doc_strategy(), max_size=50)


def unique_doc_list_strategy() -> SearchStrategy[list[RawDoc]]:
    """Strategy emitting RawDoc lists with unique doc_id values."""
    return st.lists(raw_doc_strategy(), max_size=50, unique_by=lambda d: d.doc_id)


def env_strategy() -> SearchStrategy[RagEnv]:
    """Strategy varying RagEnv.chunk_size in a practical range."""
    return st.builds(RagEnv, chunk_size=st.integers(min_value=128, max_value=1024))


def text_node_strategy() -> SearchStrategy[TextNode]:
    return st.builds(
        TextNode,
        text=st.text(max_size=100),
        metadata=st.dictionaries(
            keys=st.just("id"),
            values=st.text(
                min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_"
            ),
            max_size=1,
        ),
    )


def tree_strategy() -> SearchStrategy[TreeDoc]:
    base = st.builds(TreeDoc, node=text_node_strategy(), children=st.just(()))
    return st.recursive(
        base,
        lambda sub: st.builds(
            TreeDoc, node=text_node_strategy(), children=st.lists(sub, max_size=3).map(tuple)
        ),
        max_leaves=50,
    )


def deep_chain(depth: int) -> TreeDoc:
    if depth < 1:
        raise ValueError("depth must be >= 1")
    node: TreeDoc = TreeDoc(TextNode(text=f"n{depth - 1}", metadata={"id": f"n{depth - 1}"}), ())
    for i in range(depth - 2, -1, -1):
        node = TreeDoc(TextNode(text=f"n{i}", metadata={"id": f"n{i}"}), (node,))
    return node


def deep_chain_strategy(depth: int) -> SearchStrategy[TreeDoc]:
    return st.just(deep_chain(depth))


@st.composite
def pipeline_chunk_strategy(draw) -> Chunk:
    """Strategy for Chunk instances respecting the production embedding invariant."""
    text = draw(st.text(min_size=1))
    start = draw(st.integers(min_value=0))
    end = start + len(text)

    # Embedding mirrors the production rule (SHA256 → 16 floats in [0.0, 1.0]).
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    step = 4
    vec = tuple(int(h[i : i + step], 16) / (16**step - 1) for i in range(0, 64, step))

    doc_id = draw(st.text(min_size=1))
    return Chunk(doc_id=doc_id, text=text, start=start, end=end, metadata={}, embedding=vec)


__all__ = [
    "SearchStrategy",
    "raw_doc_strategy",
    "doc_list_strategy",
    "unique_doc_list_strategy",
    "env_strategy",
    "text_node_strategy",
    "tree_strategy",
    "deep_chain",
    "deep_chain_strategy",
    "pipeline_chunk_strategy",
]
