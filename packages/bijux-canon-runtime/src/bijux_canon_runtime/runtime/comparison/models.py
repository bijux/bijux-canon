# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Typed policy and result models for Runtime comparison."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ComparisonDimension(StrEnum):
    """Complete supported semantic and performance comparison dimensions."""

    DAG = "dag"
    CONFIGURATION = "configuration"
    CORPUS = "corpus"
    INDEX = "index"
    MODEL = "model"
    RETRIEVAL = "retrieval"
    CLAIMS = "claims"
    CITATIONS = "citations"
    PROVIDER_CALLS = "provider-calls"
    TIMING = "timing"
    POLICY = "policy"
    OUTCOME = "outcome"


class DifferenceClassification(StrEnum):
    """Policy interpretation of one exact observed difference."""

    EQUAL = "equal"
    EXPECTED = "expected"
    BOUNDED = "bounded"
    REGRESSION = "regression"
    INCOMPARABLE = "incomparable"


@dataclass(frozen=True, slots=True)
class RuntimeComparisonPolicy:
    """Selected dimensions and explicit acceptable variance."""

    dimensions: tuple[ComparisonDimension, ...] = tuple(ComparisonDimension)
    expected_differences: tuple[ComparisonDimension, ...] = (
        ComparisonDimension.TIMING,
        ComparisonDimension.POLICY,
    )
    max_duration_delta_ms: float = 1000.0
    max_duration_ratio: float = 5.0

    def __post_init__(self) -> None:
        if (
            not self.dimensions
            or len(self.dimensions) > len(ComparisonDimension)
            or len(set(self.dimensions)) != len(self.dimensions)
        ):
            raise ValueError("comparison dimensions must be nonempty and unique")
        if len(set(self.expected_differences)) != len(self.expected_differences):
            raise ValueError("expected comparison dimensions must be unique")
        if not set(self.expected_differences).issubset(self.dimensions):
            raise ValueError("expected differences must be selected dimensions")
        if self.max_duration_delta_ms < 0 or self.max_duration_ratio < 1:
            raise ValueError("comparison timing tolerance is invalid")


@dataclass(frozen=True, slots=True)
class RuntimeDifference:
    """One typed comparison with both exact values and an explanation."""

    dimension: ComparisonDimension
    path: str
    classification: DifferenceClassification
    explanation: str
    baseline: object
    candidate: object


@dataclass(frozen=True, slots=True)
class RuntimeComparisonResult:
    """Complete cross-attempt comparison and conjunction verdict."""

    schema_version: str
    comparison_sha256: str
    baseline_run_id: str
    baseline_attempt_id: str
    candidate_run_id: str
    candidate_attempt_id: str
    equivalent: bool
    differences: tuple[RuntimeDifference, ...]


__all__ = [
    "ComparisonDimension",
    "DifferenceClassification",
    "RuntimeComparisonPolicy",
    "RuntimeComparisonResult",
    "RuntimeDifference",
]
