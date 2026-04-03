# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from typing import Any


class VectorStoreAdapter(ABC):
    """Explicit adapter surface for external vector stores (no defaults)."""

    @abstractmethod
    def connect(self) -> None:
        """Establish connectivity and validate configuration."""

    @abstractmethod
    def insert(
        self,
        vectors: Iterable[Sequence[float]],
        metadata: Iterable[dict[str, Any]] | None = None,
    ) -> list[str]:
        """Insert vectors with optional metadata and return assigned ids."""

    @abstractmethod
    def query(
        self, vector: Sequence[float], k: int, mode: str
    ) -> list[tuple[str, float]]:
        """Query the store and return (id, score) pairs."""

    @abstractmethod
    def delete(self, ids: Iterable[str]) -> int:
        """Delete vectors by id and return count removed."""


__all__ = ["VectorStoreAdapter"]
