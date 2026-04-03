# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from bijux_vex.core.execution_result import ExecutionResult
from bijux_vex.core.types import Result


@dataclass(frozen=True)
class VectorExecutionDiff:
    execution_a: ExecutionResult
    execution_b: ExecutionResult
    overlap_ratio: float
    recall_delta: float
    rank_instability: float


def compare_executions(
    execution_a: ExecutionResult,
    results_a: Iterable[Result],
    execution_b: ExecutionResult,
    results_b: Iterable[Result],
) -> VectorExecutionDiff:
    list_a = list(results_a)
    list_b = list(results_b)
    ids_a = [r.vector_id for r in list_a]
    ids_b = [r.vector_id for r in list_b]
    set_a = set(ids_a)
    set_b = set(ids_b)
    overlap = set_a & set_b
    union = set_a | set_b
    overlap_ratio = len(overlap) / len(union) if union else 1.0
    recall_delta = (len(overlap) / len(set_a) if set_a else 1.0) - (
        len(overlap) / len(set_b) if set_b else 1.0
    )
    rank_instability = _rank_instability(ids_a, ids_b, overlap)
    return VectorExecutionDiff(
        execution_a=execution_a,
        execution_b=execution_b,
        overlap_ratio=overlap_ratio,
        recall_delta=recall_delta,
        rank_instability=rank_instability,
    )


def _rank_instability(ids_a: list[str], ids_b: list[str], overlap: set[str]) -> float:
    if not overlap:
        return 1.0 if ids_a or ids_b else 0.0
    total = 0
    for vid in overlap:
        rank_a = ids_a.index(vid)
        rank_b = ids_b.index(vid)
        total += abs(rank_a - rank_b)
    return total / (len(overlap) * max(len(ids_a), len(ids_b)))


__all__ = ["compare_executions", "VectorExecutionDiff"]
