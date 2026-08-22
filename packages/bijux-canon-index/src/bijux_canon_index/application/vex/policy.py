# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Typed admission policy for verified vector executions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math

from .witnesses import ExactSearchWitness


class VexPolicyMode(StrEnum):
    """Whether a violation refuses execution or produces an explicit flag."""

    enforce = "enforce"
    report = "report"


class VexPolicyStatus(StrEnum):
    """Stable result of applying a VEX budget."""

    admitted = "admitted"
    flagged = "flagged"
    refused = "refused"


class VexPolicyViolation(StrEnum):
    """Machine-readable reasons an execution did not meet policy."""

    latency_budget_exceeded = "latency_budget_exceeded"
    memory_budget_exceeded = "memory_budget_exceeded"
    candidate_budget_exceeded = "candidate_budget_exceeded"
    ef_search_budget_exceeded = "ef_search_budget_exceeded"
    witness_required = "witness_required"
    minimum_recall_not_measured = "minimum_recall_not_measured"
    minimum_recall_not_met = "minimum_recall_not_met"
    result_unreachable = "result_unreachable"


@dataclass(frozen=True, slots=True)
class VexExecutionBudget:
    """Maximum effort and minimum quality admitted for one execution."""

    max_latency_ms: float
    max_memory_bytes: int
    max_candidates: int
    max_ef_search: int
    minimum_recall: float
    require_witness: bool = True

    def __post_init__(self) -> None:
        if not math.isfinite(self.max_latency_ms) or self.max_latency_ms <= 0:
            raise ValueError("VEX max_latency_ms must be finite and positive")
        if (
            min(
                self.max_memory_bytes,
                self.max_candidates,
                self.max_ef_search,
            )
            <= 0
        ):
            raise ValueError("VEX effort budgets must be positive")
        if not 0.0 <= self.minimum_recall <= 1.0:
            raise ValueError("VEX minimum_recall must be within [0,1]")


@dataclass(frozen=True, slots=True)
class VexExecutionObservation:
    """Measured effort, quality, and reachability for one execution."""

    latency_ms: float
    memory_bytes: int
    candidate_count: int
    ef_search: int
    recall_at_k: float | None
    result_reachability: float
    witness: ExactSearchWitness | None

    def __post_init__(self) -> None:
        if not math.isfinite(self.latency_ms) or self.latency_ms < 0:
            raise ValueError("VEX observed latency must be finite and non-negative")
        if min(self.memory_bytes, self.candidate_count, self.ef_search) < 0:
            raise ValueError("VEX observed effort must be non-negative")
        if self.recall_at_k is not None and not 0.0 <= self.recall_at_k <= 1.0:
            raise ValueError("VEX observed recall must be within [0,1]")
        if not 0.0 <= self.result_reachability <= 1.0:
            raise ValueError("VEX result reachability must be within [0,1]")


@dataclass(frozen=True, slots=True)
class VexPolicyDecision:
    """Typed admission result retaining every observed violation."""

    schema_version: str
    status: VexPolicyStatus
    violations: tuple[VexPolicyViolation, ...]


def evaluate_vex_budget(
    budget: VexExecutionBudget,
    observation: VexExecutionObservation,
    *,
    mode: VexPolicyMode = VexPolicyMode.enforce,
) -> VexPolicyDecision:
    """Apply all effort, witness, quality, and reachability bounds."""

    violations = []
    if observation.latency_ms > budget.max_latency_ms:
        violations.append(VexPolicyViolation.latency_budget_exceeded)
    if observation.memory_bytes > budget.max_memory_bytes:
        violations.append(VexPolicyViolation.memory_budget_exceeded)
    if observation.candidate_count > budget.max_candidates:
        violations.append(VexPolicyViolation.candidate_budget_exceeded)
    if observation.ef_search > budget.max_ef_search:
        violations.append(VexPolicyViolation.ef_search_budget_exceeded)
    if budget.require_witness and observation.witness is None:
        violations.append(VexPolicyViolation.witness_required)
    if observation.recall_at_k is None:
        violations.append(VexPolicyViolation.minimum_recall_not_measured)
    elif observation.recall_at_k < budget.minimum_recall:
        violations.append(VexPolicyViolation.minimum_recall_not_met)
    if observation.result_reachability < 1.0:
        violations.append(VexPolicyViolation.result_unreachable)

    if not violations:
        status = VexPolicyStatus.admitted
    elif mode is VexPolicyMode.report:
        status = VexPolicyStatus.flagged
    else:
        status = VexPolicyStatus.refused
    return VexPolicyDecision(
        schema_version="bijux.canon.vex.policy_decision.v1",
        status=status,
        violations=tuple(violations),
    )


__all__ = [
    "VexExecutionBudget",
    "VexExecutionObservation",
    "VexPolicyDecision",
    "VexPolicyMode",
    "VexPolicyStatus",
    "VexPolicyViolation",
    "evaluate_vex_budget",
]
