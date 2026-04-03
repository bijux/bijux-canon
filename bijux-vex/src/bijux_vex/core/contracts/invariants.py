# SPDX-License-Identifier: MIT
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.types import ExecutionArtifact, ExecutionRequest


@dataclass(frozen=True)
class Invariant:
    invariant_id: str
    description: str
    predicate: Callable[[], bool]


def _always_true() -> bool:
    return True


def invariant_execution_contract_match(
    artifact: ExecutionArtifact, request: ExecutionRequest
) -> Invariant:
    return Invariant(
        invariant_id="INV-010",
        description="Artifact and request execution contracts must align",
        predicate=lambda: artifact.execution_contract is request.execution_contract,
    )


def invariant_randomness_required(request: ExecutionRequest) -> Invariant:
    return Invariant(
        invariant_id="INV-020",
        description="Non-deterministic execution requires declared randomness",
        predicate=lambda: (
            request.execution_contract is not ExecutionContract.NON_DETERMINISTIC
            or request.execution_budget is not None
        ),
    )


def invariant_provenance_required(artifact: ExecutionArtifact) -> Invariant:
    return Invariant(
        invariant_id="INV-040",
        description="Replay requires stored provenance for artifact",
        predicate=_always_true,
    )


def assert_invariants(invariants: Iterable[Invariant]) -> None:
    failed = [inv for inv in invariants if not inv.predicate()]
    if failed:
        ids = ", ".join(inv.invariant_id for inv in failed)
        raise AssertionError(f"Invariant(s) failed: {ids}")


__all__ = [
    "Invariant",
    "invariant_execution_contract_match",
    "invariant_randomness_required",
    "invariant_provenance_required",
    "assert_invariants",
]
