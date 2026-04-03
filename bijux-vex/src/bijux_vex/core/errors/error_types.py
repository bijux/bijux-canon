# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""
Backend-agnostic error taxonomy with retry hints.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BijuxError(Exception):
    message: str
    invariant_id: str = "INV-000"
    retryable: bool = False

    def __str__(self) -> str:
        if self.invariant_id:
            return f"[{self.invariant_id}] {self.message}"
        return self.message


# Domain-level errors
class ValidationError(BijuxError):
    """Input failed validation."""


class InvariantError(BijuxError):
    """Domain invariant was violated."""

    def __init__(
        self, message: str, *, invariant_id: str = "INV-000", retryable: bool = False
    ) -> None:
        super().__init__(
            message=message, invariant_id=invariant_id, retryable=retryable
        )


class NotFoundError(BijuxError):
    """Requested entity does not exist."""


class ConflictError(BijuxError):
    """State conflict such as duplicate insert or version mismatch."""


# Operational errors
class ConfigurationError(BijuxError):
    """Configuration is invalid or incomplete."""


class DeterminismViolationError(BijuxError):
    """Determinism contract cannot be honored."""


class BackendUnavailableError(BijuxError):
    """Backend is unavailable or locked."""


class CorruptArtifactError(BijuxError):
    """Stored artifact or index is corrupted or incompatible."""


# Contract errors
class AtomicityViolationError(BijuxError):
    """A transactional boundary was broken."""


class AuthzDeniedError(BijuxError):
    """Authorization check rejected the operation."""


class BackendDivergenceError(BijuxError):
    """Backend observed non-deterministic or inconsistent behavior."""


class ReplayNotSupportedError(BijuxError):
    """Replay attempted on a non-replayable execution contract."""


class BudgetExceededError(BijuxError):
    """Execution exceeded an enforced budget."""

    def __init__(
        self,
        message: str,
        *,
        invariant_id: str = "INV-021",
        retryable: bool = False,
        dimension: str | None = None,
        partial_results: tuple[object, ...] = (),
    ) -> None:
        super().__init__(
            message=message, invariant_id=invariant_id, retryable=retryable
        )
        self.dimension = dimension or "unknown"
        self.partial_results = partial_results


class BackendCapabilityError(BijuxError):
    """Raised when backend capabilities cannot satisfy a request."""

    status = 503


class NDExecutionUnavailableError(BijuxError):
    """Non-deterministic execution requested without ANN support."""

    status = 503

    def __init__(
        self,
        message: str,
        *,
        capability: str | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message=message, retryable=retryable)
        self.capability = capability or "ann_support"


class AnnIndexBuildError(BijuxError):
    """Raised when ANN index construction fails."""


class AnnQueryError(BijuxError):
    """Raised when ANN query fails."""


class AnnBudgetError(BudgetExceededError):
    """Raised when ANN execution exceeds configured budgets."""


class PluginError(BijuxError):
    """Base class for plugin-related failures."""


class PluginLoadError(PluginError):
    """Raised when a plugin fails to load or initialize."""


class PluginTimeoutError(PluginError):
    """Raised when a plugin call exceeds the allowed timeout."""


def mark_retryable(error: BijuxError) -> BijuxError:
    """Return a copy of the error marked retryable without changing type."""
    return type(error)(message=str(error), retryable=True)


__all__ = [
    "BijuxError",
    "ValidationError",
    "InvariantError",
    "NotFoundError",
    "ConflictError",
    "ConfigurationError",
    "DeterminismViolationError",
    "BackendUnavailableError",
    "CorruptArtifactError",
    "AtomicityViolationError",
    "AuthzDeniedError",
    "BackendDivergenceError",
    "BackendCapabilityError",
    "ReplayNotSupportedError",
    "BudgetExceededError",
    "AnnIndexBuildError",
    "AnnQueryError",
    "AnnBudgetError",
    "PluginError",
    "PluginLoadError",
    "PluginTimeoutError",
    "mark_retryable",
]
