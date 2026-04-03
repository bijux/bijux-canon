# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from bijux_vex.contracts.resources import VectorSource
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.runtime.vector_execution import VectorExecution
from bijux_vex.core.types import ExecutionArtifact, ExecutionRequest, Result


class VectorExecutionAlgorithm(ABC):
    name: str
    supported_contracts: set[ExecutionContract]

    @abstractmethod
    def plan(
        self,
        artifact: ExecutionArtifact,
        request: ExecutionRequest,
        backend_id: str,
    ) -> VectorExecution: ...

    @abstractmethod
    def execute(
        self,
        execution: VectorExecution,
        artifact: ExecutionArtifact,
        vectors: VectorSource,
    ) -> Iterable[Result]: ...


_REGISTRY: dict[str, VectorExecutionAlgorithm] = {}


def register_algorithm(algorithm: VectorExecutionAlgorithm) -> None:
    _REGISTRY[algorithm.name] = algorithm


def get_algorithm(name: str) -> VectorExecutionAlgorithm:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown execution algorithm '{name}'")
    return _REGISTRY[name]


def list_algorithms() -> set[str]:
    return set(_REGISTRY)


__all__ = [
    "VectorExecutionAlgorithm",
    "register_algorithm",
    "get_algorithm",
    "list_algorithms",
    "VectorExecution",
]
