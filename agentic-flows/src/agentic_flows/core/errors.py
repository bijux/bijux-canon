# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for core/errors.py."""

from __future__ import annotations

from enum import Enum


class ResolutionFailure(Exception):  # noqa: N818
    """Resolution failure; misuse breaks planning guarantees."""


class ExecutionFailure(Exception):  # noqa: N818
    """Execution failure; misuse breaks run integrity."""


class RetrievalFailure(Exception):  # noqa: N818
    """Retrieval failure; misuse breaks evidence integrity."""


class ReasoningFailure(Exception):  # noqa: N818
    """Reasoning failure; misuse breaks claim integrity."""


class VerificationFailure(Exception):  # noqa: N818
    """Verification failure; misuse breaks verification trust."""


class NonDeterminismViolationError(RuntimeError):
    """Non-determinism violation; misuse breaks governance."""


class SemanticViolationError(RuntimeError):
    """Semantic violation; misuse breaks authority guarantees."""


class ConfigurationError(ValueError):
    """Configuration error; misuse breaks execution setup."""


class FailureClass(str, Enum):
    # Order is stable; ordinal values are part of the external contract. Reordering is forbidden.
    """Failure classes; misuse breaks failure taxonomy."""

    STRUCTURAL = "structural"
    SEMANTIC = "semantic"
    ENVIRONMENTAL = "environmental"
    AUTHORITY = "authority"


FAILURE_CLASS_MAP = {
    ResolutionFailure: FailureClass.STRUCTURAL,
    ExecutionFailure: FailureClass.STRUCTURAL,
    RetrievalFailure: FailureClass.STRUCTURAL,
    ReasoningFailure: FailureClass.STRUCTURAL,
    VerificationFailure: FailureClass.SEMANTIC,
    NonDeterminismViolationError: FailureClass.SEMANTIC,
    SemanticViolationError: FailureClass.AUTHORITY,
    ConfigurationError: FailureClass.STRUCTURAL,
}


def classify_failure(exc: BaseException) -> FailureClass:
    """Classify failure; misuse breaks operator response."""
    for failure_type, failure_class in FAILURE_CLASS_MAP.items():
        if isinstance(exc, failure_type):
            return failure_class
    raise KeyError(f"Unclassified failure: {type(exc).__name__}")


__all__ = [
    "ResolutionFailure",
    "ExecutionFailure",
    "RetrievalFailure",
    "ReasoningFailure",
    "VerificationFailure",
    "NonDeterminismViolationError",
    "SemanticViolationError",
    "ConfigurationError",
    "FailureClass",
    "FAILURE_CLASS_MAP",
    "classify_failure",
]
