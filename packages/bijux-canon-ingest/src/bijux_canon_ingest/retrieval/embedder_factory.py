# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Shared embedder selection helpers for retrieval workflows."""

from __future__ import annotations

from bijux_canon_ingest.retrieval.embedders import (
    HashEmbedder,
    SentenceTransformersEmbedder,
)
from bijux_canon_ingest.retrieval.ports import Embedder


def build_embedder(
    backend: str,
    *,
    sbert_model: str = "all-MiniLM-L6-v2",
) -> Embedder:
    """Construct an embedder from a configured backend name."""

    if backend == "hash16":
        return HashEmbedder()
    if backend == "sbert":
        return SentenceTransformersEmbedder(model_name=sbert_model)
    raise ValueError(f"unknown embedder backend: {backend}")


def embedder_for_model(model_name: str) -> Embedder:
    """Resolve an embedder instance from a persisted index model descriptor."""

    if model_name.startswith("sbert:"):
        return SentenceTransformersEmbedder(model_name=model_name.split(":", 1)[1])
    return HashEmbedder()


__all__ = ["build_embedder", "embedder_for_model"]
