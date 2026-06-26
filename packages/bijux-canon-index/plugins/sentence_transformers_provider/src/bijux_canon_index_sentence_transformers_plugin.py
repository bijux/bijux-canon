# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import sentence_transformers
from sentence_transformers import SentenceTransformer

from bijux_canon_index.infra.embeddings.cache import embedding_config_hash
from bijux_canon_index.infra.embeddings.registry import (
    EmbeddingBatch,
    EmbeddingMetadata,
    EmbeddingProvider,
    EmbeddingProviderRegistry,
)
from bijux_canon_index.infra.plugins.contract import PluginContract


class SentenceTransformersProvider(EmbeddingProvider):
    """Embedding provider backed by sentence-transformers."""

    name = "sentence_transformers"

    @property
    def provider_version(self) -> str | None:
        """Return the provider library version."""
        return getattr(sentence_transformers, "__version__", None)

    def embed(
        self, texts: list[str], model: str, options: Mapping[str, str] | None = None
    ) -> EmbeddingBatch:
        """Encode texts into float32 vectors."""
        if not model:
            raise ValueError("model id required for embeddings")
        resolved_options = dict(options or {})
        resolved_options.setdefault("normalize", "false")
        device = resolved_options.get("device")
        encoder = SentenceTransformer(model, device=device)
        vectors = encoder.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=resolved_options["normalize"].lower() == "true",
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
            embedding_normalization=resolved_options["normalize"],
            config_hash=embedding_config_hash(
                self.name,
                model,
                resolved_options,
                provider_version=self.provider_version,
            ),
        )
        return EmbeddingBatch(
            vectors=[tuple(map(float, row)) for row in vectors.tolist()],
            metadata=metadata,
        )


def register(registry: EmbeddingProviderRegistry) -> None:
    """Register the sentence-transformers embedding provider."""
    registry.register(
        SentenceTransformersProvider.name,
        factory=SentenceTransformersProvider,
        contract=PluginContract(
            determinism="model_dependent",
            randomness_sources=("model_init", "runtime_device"),
            approximation=False,
        ),
        default=True,
    )
