# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Sentence transformers helpers."""

from __future__ import annotations

from collections.abc import Mapping

try:  # pragma: no cover - optional dependency
    import sentence_transformers
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional dependency
    sentence_transformers = None
    SentenceTransformer = None

from bijux_canon_index.infra.embeddings.cache import embedding_config_hash
from bijux_canon_index.infra.embeddings.registry import (
    EmbeddingBatch,
    EmbeddingMetadata,
    EmbeddingProvider,
)
import numpy as np


class SentenceTransformersProvider(EmbeddingProvider):
    """Represents sentence transformers provider."""
    name = "sentence_transformers"

    @property
    def provider_version(self) -> str | None:
        """Handle provider version."""
        return getattr(sentence_transformers, "__version__", None)

    def embed(
        self, texts: list[str], model: str, options: Mapping[str, str] | None = None
    ) -> EmbeddingBatch:
        """Handle embed."""
        if (
            sentence_transformers is None or SentenceTransformer is None
        ):  # pragma: no cover
            raise ImportError("sentence-transformers is not available")
        if not model:
            raise ValueError("model id required for embeddings")
        options = dict(options or {})
        options.setdefault("normalize", "false")
        device = options.get("device")
        encoder = SentenceTransformer(model, device=device)
        vectors = encoder.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=options.get("normalize", "false").lower() == "true",
            show_progress_bar=False,
        )
        vectors = np.asarray(vectors, dtype="float32")
        metadata = EmbeddingMetadata(
            provider=self.name,
            provider_version=self.provider_version,
            model=model,
            model_version=getattr(sentence_transformers, "__version__", None),
            embedding_determinism="model_dependent",
            embedding_seed=None,
            embedding_device=str(getattr(encoder, "device", device) or ""),
            embedding_dtype=str(vectors.dtype),
            embedding_normalization=options.get("normalize"),
            config_hash=embedding_config_hash(
                self.name, model, options, provider_version=self.provider_version
            ),
        )
        return EmbeddingBatch(
            vectors=[tuple(map(float, row)) for row in vectors.tolist()],
            metadata=metadata,
        )


__all__ = ["SentenceTransformersProvider"]
