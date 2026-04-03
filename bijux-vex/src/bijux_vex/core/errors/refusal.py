# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_vex.core import errors


def is_refusal(exc: Exception) -> bool:
    return isinstance(
        exc,
        (
            errors.BudgetExceededError,
            errors.ConfigurationError,
            errors.DeterminismViolationError,
            errors.BackendUnavailableError,
            errors.BackendCapabilityError,
        ),
    )


def refusal_payload(exc: Exception) -> dict[str, object]:
    if isinstance(exc, errors.DeterminismViolationError):
        return {
            "reason": "determinism_violation",
            "message": str(exc),
            "remediation": (
                "Use deterministic inputs or switch to non_deterministic contract "
                "with declared randomness."
            ),
        }
    if isinstance(exc, errors.BackendCapabilityError):
        return {
            "reason": "backend_capability_missing",
            "message": str(exc),
            "remediation": (
                "Select a backend that supports the requested capability or "
                "change the request."
            ),
        }
    if isinstance(exc, errors.BackendUnavailableError):
        return {
            "reason": "backend_unavailable",
            "message": str(exc),
            "remediation": "Verify backend connectivity/credentials and retry.",
        }
    if isinstance(exc, errors.ConfigurationError):
        return {
            "reason": "configuration_error",
            "message": str(exc),
            "remediation": "Fix configuration and retry.",
        }
    if isinstance(exc, errors.BudgetExceededError):
        return {
            "reason": "budget_exceeded",
            "message": str(exc),
            "remediation": "Reduce request size or relax the configured limits.",
        }
    return {"reason": "unknown", "message": str(exc), "remediation": "Inspect logs."}


__all__ = ["is_refusal", "refusal_payload"]
