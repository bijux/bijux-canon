# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""Failure taxonomy and deterministic retry orchestration."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import TypeVar

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors.error_types import BijuxError, InvariantError, mark_retryable

T = TypeVar("T")


class FailureKind(Enum):
    RETRYABLE = "retryable"
    TERMINAL = "terminal"
    DIVERGENCE = "divergence"


def classify_failure(error: Exception) -> FailureKind:
    if isinstance(error, InvariantError):
        return FailureKind.TERMINAL
    if isinstance(error, BijuxError) and error.retryable:
        return FailureKind.RETRYABLE
    return FailureKind.TERMINAL


def retry_with_policy(
    fn: Callable[[], T],
    attempts: int = 3,
    contract: ExecutionContract | None = None,
) -> T:
    last_error: Exception | None = None
    allowed_attempts = retry_budget(contract, attempts)
    for _ in range(allowed_attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if allowed_attempts == 1:
                raise
            if classify_failure(exc) is not FailureKind.RETRYABLE:
                raise
    if last_error is None:
        raise RuntimeError(
            "retry_with_policy exhausted attempts without capturing error"
        )
    raise last_error


FAILURE_ACTIONS: dict[FailureKind, str] = {
    FailureKind.RETRYABLE: "retry",
    FailureKind.DIVERGENCE: "alert",
    FailureKind.TERMINAL: "escalate",
}


def action_for_failure(error: Exception) -> str:
    """Return operator action for a given failure."""
    return FAILURE_ACTIONS.get(classify_failure(error), "escalate")


def retry_budget(contract: ExecutionContract | None, default_attempts: int) -> int:
    """Centralized retry budget calculation for all callers."""
    return 1 if contract is ExecutionContract.DETERMINISTIC else default_attempts


__all__ = [
    "FailureKind",
    "classify_failure",
    "retry_with_policy",
    "mark_retryable",
    "FAILURE_ACTIONS",
    "action_for_failure",
    "retry_budget",
]
