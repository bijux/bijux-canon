# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import numpy as np
from hypothesis import given
from hypothesis import strategies as st

from bijux_rag.fp.validation import VFailure, VSuccess
from bijux_rag.rag.domain import Chunk, ChunkMetadata, ChunkText, process_batch_hybrid

chunk_strat = st.builds(
    Chunk,
    text=st.builds(ChunkText, content=st.text(min_size=1, max_size=100)),
    metadata=st.builds(
        ChunkMetadata,
        source=st.text(max_size=20),
        tags=st.lists(st.text(min_size=1, max_size=10), max_size=5).map(tuple),
        embedding_model=st.none() | st.text(min_size=1, max_size=10),
        expected_dim=st.none(),
    ),
    embedding=st.none(),
)


@given(batch=st.lists(chunk_strat, min_size=1, max_size=50))
def test_pure_vs_hybrid_equivalence(batch: list[Chunk]) -> None:
    pure = process_batch_hybrid(batch, mode="pure")
    hybrid = process_batch_hybrid(batch, mode="hybrid")
    assert len(pure) == len(hybrid)
    for p, h in zip(pure, hybrid):
        if isinstance(p, VSuccess):
            assert isinstance(h, VSuccess)
            pc = p.value
            hc = h.value
            assert pc.id == hc.id
            assert pc.text.content == hc.text.content
            assert pc.metadata == hc.metadata
            assert (pc.embedding is None) == (hc.embedding is None)
            assert pc.embedding is not None and hc.embedding is not None
            assert pc.embedding.model == hc.embedding.model
            assert np.allclose(pc.embedding.vector, hc.embedding.vector, rtol=1e-6, atol=1e-8)
        else:
            assert isinstance(h, VFailure)
            assert p.errors == h.errors
