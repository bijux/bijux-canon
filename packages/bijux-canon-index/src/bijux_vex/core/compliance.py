# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""Compliance policies for execution comparisons."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_vex.core.errors import InvariantError
from bijux_vex.domain.execution_requests.compare import VectorExecutionDiff


@dataclass(frozen=True)
class ComparisonPolicy:
    min_recall: float = 0.0
    max_rank_instability: float = 1.0


def enforce_policy(diff: VectorExecutionDiff, policy: ComparisonPolicy) -> None:
    if diff.recall_delta < (policy.min_recall - 1):
        raise InvariantError(message="Comparison policy violated: recall below minimum")
    if diff.rank_instability > policy.max_rank_instability:
        raise InvariantError(
            message="Comparison policy violated: rank instability too high"
        )


__all__ = ["ComparisonPolicy", "enforce_policy"]
