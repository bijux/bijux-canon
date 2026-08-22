# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Embedding value objects for retrieval-domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
import math


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
