"""Termination metadata for pipeline executions."""

from __future__ import annotations

from enum import Enum


class ExecutionTerminationReason(str, Enum):
    """Why a pipeline execution stopped."""

    COMPLETED = "completed"
    CONVERGENCE = "convergence"
    FAILURE = "failure"
    USER_ABORT = "user_abort"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
