# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import pytest

from bijux_canon_ingest.retrieval.embedder_factory import (
    build_embedder,
    embedder_for_model,
)
from bijux_canon_ingest.retrieval.embedders import (
    HashEmbedder,
    SentenceTransformersEmbedder,
)


def test_build_embedder_selects_hash_backend() -> None:
    assert isinstance(build_embedder("hash16"), HashEmbedder)


def test_build_embedder_selects_sentence_transformers_backend() -> None:
    embedder = build_embedder("sbert", sbert_model="all-MiniLM-L6-v2")

    assert isinstance(embedder, SentenceTransformersEmbedder)
    assert embedder.model_name == "all-MiniLM-L6-v2"


def test_embedder_for_model_selects_hash_embedder() -> None:
    assert isinstance(embedder_for_model("hash16"), HashEmbedder)


def test_embedder_for_model_selects_sentence_transformers_embedder() -> None:
    embedder = embedder_for_model("sbert:all-MiniLM-L6-v2")

    assert isinstance(embedder, SentenceTransformersEmbedder)
    assert embedder.model_name == "all-MiniLM-L6-v2"


def test_build_embedder_rejects_unknown_backend() -> None:
    with pytest.raises(ValueError, match="unknown embedder backend"):
        build_embedder("unknown")
