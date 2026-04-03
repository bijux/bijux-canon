# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG subsystem ADT: embeddings (end-of-Bijux RAG; domain-modeling)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Embedding:
    vector: tuple[float, ...]
    model: str
    dim: int = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "dim", len(self.vector))
        for i, v in enumerate(self.vector):
            if not math.isfinite(v):
                raise ValueError(f"embedding[{i}] must be finite")


__all__ = ["Embedding"]
