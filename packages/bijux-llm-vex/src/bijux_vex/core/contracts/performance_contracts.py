# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""Lightweight performance envelopes for execution results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import InvariantError

if TYPE_CHECKING:
    from bijux_vex.core.execution_result import ExecutionResult


@dataclass(frozen=True)
class PerformanceEnvelope:
    name: str
    description: str
    max_rank_instability: float | None = None
    min_recall: float | None = None


EXACT_ENVELOPE = PerformanceEnvelope(
    name="exact",
    description="O(N·d) exact execution; rank instability must be zero.",
    max_rank_instability=0.0,
    min_recall=1.0,
)

APPROX_ENVELOPE = PerformanceEnvelope(
    name="approx",
    description="Approximate execution with bounded recall and cost.",
    max_rank_instability=0.5,
    min_recall=0.5,
)


def assert_performance_envelope(
    result: ExecutionResult, contract: ExecutionContract
) -> None:
    if contract is ExecutionContract.DETERMINISTIC:
        envelope = EXACT_ENVELOPE
        if result.cost.distance_computations < len(result.results):
            raise InvariantError(
                message="Deterministic execution cost under-reported distance computations"
            )
        if result.approximation is not None:
            raise InvariantError(
                message="Deterministic execution must not emit approximation report"
            )
    else:
        envelope = APPROX_ENVELOPE
        if result.approximation is None:
            raise InvariantError(
                message="Approximate execution must emit approximation report"
            )
        if result.cost.graph_hops < len(result.results):
            raise InvariantError(
                message="Approximate execution must report graph hops at least equal to result count"
            )
    if (
        envelope.min_recall is not None
        and result.results
        and result.approximation
        and result.approximation.recall_at_k < envelope.min_recall
    ):
        raise InvariantError(message="Approximate execution recall fell below envelope")


__all__ = [
    "PerformanceEnvelope",
    "EXACT_ENVELOPE",
    "APPROX_ENVELOPE",
    "assert_performance_envelope",
]
