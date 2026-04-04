# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from bijux_canon_ingest.application.pipeline_observations import (
    build_observations,
    tap_items,
)
from bijux_canon_ingest.core.types import Chunk, CleanDoc, EmbeddingSpec, RawDoc


def test_tap_items_returns_original_sequence_and_notifies_handler() -> None:
    seen: list[tuple[int, ...]] = []
    items = [1, 2, 3]

    returned = tap_items(items, lambda values: seen.append(values))

    assert returned is items
    assert seen == [(1, 2, 3)]


def test_build_observations_uses_sample_window() -> None:
    docs = [
        RawDoc(doc_id="d1", title="One", abstract="alpha", categories="cs.AI"),
        RawDoc(doc_id="d2", title="Two", abstract="beta", categories="cs.AI"),
    ]
    cleaned = [
        CleanDoc(doc_id="d1", title="One", abstract="alpha", categories="cs.AI"),
        CleanDoc(doc_id="d2", title="Two", abstract="beta", categories="cs.AI"),
    ]
    chunks = [
        Chunk(
            doc_id="d1",
            text="alpha",
            start=0,
            end=5,
            metadata={},
            embedding=(0.1,),
            embedding_spec=EmbeddingSpec(model="hash16", dim=1),
        ),
        Chunk(
            doc_id="d2",
            text="beta",
            start=5,
            end=9,
            metadata={},
            embedding=(0.2,),
            embedding_spec=EmbeddingSpec(model="hash16", dim=1),
        ),
    ]

    observations = build_observations(
        docs=docs,
        kept_docs=docs,
        cleaned_docs=cleaned,
        chunks=chunks,
        sample_size=1,
    )

    assert observations.total_docs == 2
    assert observations.total_chunks == 2
    assert observations.sample_doc_ids == ("d1",)
    assert observations.sample_chunk_starts == (0,)
