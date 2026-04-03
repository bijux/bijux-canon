# SPDX-License-Identifier: MIT
from __future__ import annotations

from dataclasses import dataclass

from bijux_vex.core.execution_result import ApproximationReport


@dataclass(frozen=True)
class ANNResultMetadata:
    algorithm: str
    index_params: tuple[tuple[str, str | int | float], ...]
    query_params: tuple[tuple[str, str | int | float], ...]
    recall_estimate: float
    epsilon: float
    n_candidates: int
    random_seed: int | None
    randomness_source: tuple[str, ...]
    index_hash: str | None = None


def derive_metadata(report: ApproximationReport) -> ANNResultMetadata:
    return ANNResultMetadata(
        algorithm=report.algorithm,
        index_params=tuple(report.index_parameters),
        query_params=tuple(report.query_parameters),
        recall_estimate=report.recall_at_k,
        epsilon=report.distance_error,
        n_candidates=report.n_candidates,
        random_seed=report.random_seed,
        randomness_source=report.randomness_sources,
        index_hash=report.index_hash,
    )


__all__ = ["ANNResultMetadata", "derive_metadata"]
