# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Bounded deterministic inference over a verified local embedding model."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import importlib
from pathlib import Path
from typing import Any

from bijux_canon_index.domain.embedding import EmbeddingModelLock
from bijux_canon_index.infra.embeddings.model_cache import verify_materialized_model

INFERENCE_THREADS = 1


@dataclass(frozen=True, slots=True)
class EmbeddedBatch:
    """Ordered vectors and the complete model identity that produced them."""

    vectors: tuple[tuple[float, ...], ...]
    model_lock_id: str
    device: str
    batch_size: int
    inference_threads: int = INFERENCE_THREADS


ModelLoader = Callable[[Path, str], Any]


def _load_model(model_root: Path, device: str) -> Any:
    torch = importlib.import_module("torch")
    torch.set_num_threads(INFERENCE_THREADS)
    module = importlib.import_module("sentence_transformers")
    return module.SentenceTransformer(
        str(model_root),
        device=device,
        local_files_only=True,
    )


class LocalEmbeddingModel:
    """Offline-only embedding inference with locked numeric semantics."""

    def __init__(
        self,
        model_root: str | Path,
        lock: EmbeddingModelLock,
        *,
        batch_size: int = 32,
        device: str = "cpu",
        loader: ModelLoader = _load_model,
    ) -> None:
        if batch_size < 1 or batch_size > 1024:
            raise ValueError("embedding batch size must be within 1..1024")
        if device not in {"cpu", "cuda", "mps"}:
            raise ValueError("embedding device must be explicit: cpu, cuda, or mps")
        self.model_root = Path(model_root)
        self.lock = lock
        self.batch_size = batch_size
        self.device = device
        verify_materialized_model(self.model_root, lock)
        self._model = loader(self.model_root, device)

    @property
    def model_lock_id(self) -> str:
        """Return the immutable model identity used for every emitted vector."""

        return self.lock.lock_id

    def embed(self, texts: Sequence[str]) -> EmbeddedBatch:
        """Embed non-empty canonical texts while preserving caller order."""

        values = tuple(texts)
        if not values or any(not isinstance(text, str) or not text for text in values):
            raise ValueError("embedding input must contain non-empty strings")
        encoded = self._model.encode(
            list(values),
            batch_size=self.batch_size,
            normalize_embeddings=self.lock.profile.normalization == "l2",
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        dtype = str(encoded.dtype)
        if dtype != self.lock.profile.dtype:
            raise ValueError(
                f"embedding output dtype mismatch: expected {self.lock.profile.dtype}, got {dtype}"
            )
        vectors = tuple(tuple(float(value) for value in row) for row in encoded)
        if len(vectors) != len(values):
            raise ValueError("embedding output count does not match input count")
        for vector in vectors:
            self.lock.validate_vector(vector)
        return EmbeddedBatch(
            vectors=vectors,
            model_lock_id=self.lock.lock_id,
            device=self.device,
            batch_size=self.batch_size,
            inference_threads=INFERENCE_THREADS,
        )


__all__ = ["EmbeddedBatch", "INFERENCE_THREADS", "LocalEmbeddingModel"]
