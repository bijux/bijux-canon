# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Reference embedders.

Backends:
* HashEmbedder: deterministic (demo/CI safe), small, dependency-free.
* SentenceTransformersEmbedder: optional, requires `sentence-transformers`.

All embedders must:
1) return float32 vectors
2) be deterministic in the `ci` profile
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Sequence

import numpy as np
from numpy.typing import NDArray

from bijux_rag.core.rag_types import EmbeddingSpec


def _l2_normalize(x: NDArray[np.float32]) -> NDArray[np.float32]:
    denom = np.linalg.norm(x, axis=1, keepdims=True)
    denom = np.maximum(denom, np.float32(1e-12))
    return np.asarray(x / denom, dtype=np.float32)


@dataclass(frozen=True, slots=True)
class HashEmbedder:
    """Deterministic hash-based embedder.

    This is *not* semantically meaningful. It exists for:
    - tiny unit tests
    - deterministic baselines
    - development without model downloads
    """

    _spec: EmbeddingSpec = EmbeddingSpec(model="hash16", dim=16, metric="cosine", normalized=True)

    @property
    def spec(self) -> EmbeddingSpec:
        return self._spec

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        """Return list of tuple embeddings (compat with new RagApp)."""

        arr = self.embed_texts(texts)
        return [tuple(map(float, vec)) for vec in arr.tolist()]

    def embed_texts(self, texts: Sequence[str]) -> NDArray[np.float32]:
        dim = self._spec.dim
        out = np.empty((len(texts), dim), dtype=np.float32)
        for i, t in enumerate(texts):
            h = sha256(t.encode("utf-8")).digest()
            # Split digest evenly across dim (dim must be <= len(h)).
            step = max(1, len(h) // dim)
            vec: list[float] = []
            for j in range(dim):
                chunk = h[j * step : (j + 1) * step]
                n = int.from_bytes(chunk, "big")
                denom = float(2 ** (8 * len(chunk)) - 1)
                vec.append(n / denom)
            out[i] = np.asarray(vec, dtype=np.float32)
        return _l2_normalize(out) if self._spec.normalized else out


@dataclass(frozen=True, slots=True)
class SentenceTransformersEmbedder:
    """Sentence-Transformers embedder (optional dependency)."""

    model_name: str = "all-MiniLM-L6-v2"
    normalize: bool = True

    @property
    def spec(self) -> EmbeddingSpec:
        # Dim is resolved lazily from the model, but we still expose a placeholder.
        # The index builder will overwrite with the true dim after first encode.
        return EmbeddingSpec(
            model=f"sbert:{self.model_name}", dim=384, metric="cosine", normalized=self.normalize
        )

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        return [tuple(map(float, v)) for v in self.embed_texts(texts)]

    def embed_texts(self, texts: Sequence[str]) -> NDArray[np.float32]:
        try:
            st = __import__("sentence_transformers", fromlist=["SentenceTransformer"])
        except Exception as exc:  # pragma: no cover
            raise ImportError(
                "sentence-transformers is not installed. Install extras or use --embedder hash16."
            ) from exc

        SentenceTransformer = st.SentenceTransformer
        model = SentenceTransformer(self.model_name)
        vecs = model.encode(list(texts), normalize_embeddings=self.normalize)
        arr = np.asarray(vecs, dtype=np.float32)
        # Safety: ensure finiteness.
        if not np.isfinite(arr).all():
            raise ValueError("non-finite embedding values")
        return arr


__all__ = ["HashEmbedder", "SentenceTransformersEmbedder"]
