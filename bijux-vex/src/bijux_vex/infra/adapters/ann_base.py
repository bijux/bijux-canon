# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import InvariantError
from bijux_vex.core.execution_result import ApproximationReport
from bijux_vex.core.types import ExecutionArtifact, ExecutionRequest, Result, Vector


class AnnExecutionRequestRunner(ABC):
    """Approximate execution runner. Provides no determinism guarantees."""

    force_fallback: bool = False

    @property
    @abstractmethod
    def randomness_sources(self) -> tuple[str, ...]:
        """Describe non-deterministic inputs (e.g. ANN seed, hardware variance)."""

    @property
    @abstractmethod
    def reproducibility_bounds(self) -> str:
        """Human-readable bound on how far results may diverge across runs."""

    @property
    def supports_seed(self) -> bool:
        return False

    @property
    def supports_incremental(self) -> bool:
        return False

    @property
    def supports_compaction(self) -> bool:
        return False

    def ensure_contract(self, artifact: ExecutionArtifact) -> None:
        if artifact.execution_contract is ExecutionContract.DETERMINISTIC:
            raise InvariantError(
                message="ANN runner refuses deterministic execution_contract"
            )

    def deterministic_fallback(
        self, artifact_id: str, request: ExecutionRequest
    ) -> Iterable[Result]:
        """Optional deterministic fallback; override in ANN runners."""
        raise InvariantError(
            message="Deterministic fallback not implemented for ANN runner"
        )

    def build_index(
        self,
        artifact_id: str,
        vectors: Iterable[Vector],
        metric: str,
        nd_settings: object | None = None,
    ) -> dict[str, object]:
        """Optional index construction step."""
        _ = (artifact_id, vectors, metric, nd_settings)
        return {}

    def index_info(self, artifact_id: str) -> dict[str, object]:
        """Return index metadata for introspection."""
        _ = artifact_id
        return {}

    def warmup(self, artifact_id: str, queries: Iterable[Iterable[float]]) -> None:
        _ = (artifact_id, queries)
        return None

    def compact(self, artifact_id: str, vectors: Iterable[Vector], metric: str) -> None:
        _ = (artifact_id, vectors, metric)
        return None

    def query(
        self, vector: Iterable[float], k: int, **params: object
    ) -> tuple[list[str], list[float], dict[str, object]]:
        """Return candidate ids, distances, and metadata."""
        raise InvariantError(message="ANN query not implemented")

    def set_randomness_profile(self, randomness: object | None) -> None:
        """Optional hook to pass randomness profile (e.g. seed) into the runner."""
        _ = randomness
        return None

    @abstractmethod
    def approximate_request(
        self, artifact: ExecutionArtifact, request: ExecutionRequest
    ) -> Iterable[Result]:
        """Return an approximate set of results for the given artifact/contract."""

    @abstractmethod
    def approximation_report(
        self,
        artifact: ExecutionArtifact,
        request: ExecutionRequest,
        results: Iterable[Result],
    ) -> ApproximationReport:
        """Summarize approximation behavior for auditing and replay tolerances."""


__all__ = ["AnnExecutionRequestRunner"]
