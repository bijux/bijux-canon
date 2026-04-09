# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Base helpers for domain logic."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from bijux_canon_index.contracts.resources import VectorSource
from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.runtime.vector_execution import VectorExecution
from bijux_canon_index.core.types import ExecutionArtifact, ExecutionRequest, Result


class VectorExecutionAlgorithm(ABC):
    """Represents vector execution algorithm."""

    name: str
    supported_contracts: set[ExecutionContract]

    @abstractmethod
    def plan(
        self,
        artifact: ExecutionArtifact,
        request: ExecutionRequest,
        backend_id: str,
    ) -> VectorExecution:
        """Plan vector execution for the request."""

        ...

    @abstractmethod
    def execute(
        self,
        execution: VectorExecution,
        artifact: ExecutionArtifact,
        vectors: VectorSource,
    ) -> Iterable[Result]:
        """Execute the planned vector retrieval."""

        ...


_REGISTRY: dict[str, VectorExecutionAlgorithm] = {}


def register_algorithm(algorithm: VectorExecutionAlgorithm) -> None:
    """Register algorithm."""
    _REGISTRY[algorithm.name] = algorithm


def get_algorithm(name: str) -> VectorExecutionAlgorithm:
    """Return algorithm."""
    if name not in _REGISTRY:
        raise KeyError(f"Unknown execution algorithm '{name}'")
    return _REGISTRY[name]


def list_algorithms() -> set[str]:
    """List algorithms."""
    return set(_REGISTRY)


__all__ = [
    "VectorExecutionAlgorithm",
    "register_algorithm",
    "get_algorithm",
    "list_algorithms",
    "VectorExecution",
]
