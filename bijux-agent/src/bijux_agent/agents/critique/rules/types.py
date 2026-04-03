"""Shared types for critique rule implementations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, TypedDict


@dataclass
class CriterionResult:
    """Result for a single critique criterion."""

    name: str
    result: str
    issues: list[str]
    suggestion: str
    severity: str
    confidence: float = 1.0


class CritiqueSeverity(Enum):
    """Severity levels used by the CritiqueAgent."""

    CRITICAL = "Critical"
    MAJOR = "Major"
    MINOR = "Minor"


class CritiqueAudit(TypedDict):
    """Audit metadata recorded for each critique run."""

    timestamp: str
    shards_merged: int


class CritiqueResult(TypedDict):
    """TypedDict describing the critique output schema."""

    critique_status: str
    score: float
    per_criterion: list[dict[str, Any]]
    warnings: list[str]
    issues: list[str]
    criteria: list[str]
    action_plan: list[str]
    audit: CritiqueAudit
