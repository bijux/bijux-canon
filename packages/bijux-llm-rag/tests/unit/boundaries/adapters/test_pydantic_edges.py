# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from bijux_rag.boundaries.adapters.pydantic_edges import (
    ChunkModel,
    deserialize_model,
    serialize_model,
)

nonfinite = st.sampled_from([float("nan"), float("inf"), float("-inf")])


@given(
    text=st.text(min_size=1, max_size=1000),
    metadata=st.dictionaries(st.text(), st.integers() | st.text(), max_size=20),
)
def test_chunk_roundtrip(text: str, metadata: dict[str, object]) -> None:
    model = ChunkModel(text=text, metadata=metadata)  # type: ignore[arg-type]
    json_str = serialize_model(model)
    reloaded = deserialize_model(json_str, ChunkModel)
    assert model == reloaded
    assert reloaded.length == len(text)


@given(bad_emb=st.lists(nonfinite, min_size=1))
@settings(deadline=None)
def test_nonfinite_embedding_rejected(bad_emb: list[float]) -> None:
    with pytest.raises(ValueError):
        ChunkModel(text="x", embedding=bad_emb)


@given(emb=st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=1))
def test_large_embedding_rejected_if_out_of_range(emb: list[float]) -> None:
    if any(abs(x) > 100 for x in emb):
        with pytest.raises(ValueError):
            ChunkModel(text="x", embedding=emb)


def test_schema_stable(snapshot) -> None:
    assert ChunkModel.model_json_schema() == snapshot
