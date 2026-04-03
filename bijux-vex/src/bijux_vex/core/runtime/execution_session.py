# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from bijux_vex.core.errors import InvariantError
from bijux_vex.core.identity.ids import fingerprint
from bijux_vex.core.runtime.execution_plan import ExecutionPlan
from bijux_vex.core.runtime.vector_execution import RandomnessProfile, VectorExecution
from bijux_vex.core.types import ExecutionArtifact, ExecutionRequest


class ExecutionState(StrEnum):
    CREATED = "created"
    PLANNED = "planned"
    RUNNING = "running"
    COMMITTED = "committed"
    FINALIZED = "finalized"

    def can_transition_to(self, target: ExecutionState) -> bool:
        allowed = {
            ExecutionState.CREATED: {ExecutionState.PLANNED},
            ExecutionState.PLANNED: {ExecutionState.RUNNING},
            ExecutionState.RUNNING: {
                ExecutionState.COMMITTED,
                ExecutionState.FINALIZED,
            },
            ExecutionState.COMMITTED: {ExecutionState.FINALIZED},
            ExecutionState.FINALIZED: set(),
        }
        return target in allowed[self]


def enforce_transition(
    current: ExecutionState, target: ExecutionState
) -> ExecutionState:
    if not current.can_transition_to(target):
        raise InvariantError(
            message=f"Illegal execution state transition {current.value} -> {target.value}"
        )
    return target


@dataclass(frozen=True)
class ExecutionSession:
    """Immutable execution session: the only boundary allowed to run executions."""

    session_id: str
    artifact: ExecutionArtifact
    request: ExecutionRequest
    plan: ExecutionPlan
    execution: VectorExecution
    randomness: RandomnessProfile | None
    budget: dict[str, int | float]
    state: ExecutionState = ExecutionState.CREATED


def derive_session_id(
    artifact: ExecutionArtifact,
    request: ExecutionRequest,
    plan: ExecutionPlan,
    execution: VectorExecution,
    randomness: RandomnessProfile | None,
    budget: dict[str, int | float],
    state: ExecutionState = ExecutionState.CREATED,
) -> str:
    payload = {
        "artifact": artifact.artifact_id,
        "execution_id": execution.execution_id,
        "plan_fp": plan.fingerprint,
        "contract": request.execution_contract.value,
        "mode": request.execution_mode.value
        if hasattr(request.execution_mode, "value")
        else request.execution_mode,
        "budget": tuple(sorted(budget.items())),
        "randomness": tuple(randomness.sources) if randomness else (),
        "state": state.value,
    }
    return fingerprint(payload)


__all__ = [
    "ExecutionSession",
    "derive_session_id",
    "ExecutionState",
    "enforce_transition",
]
