"""Rule-backed critique criteria execution helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from .advanced_checks import CritiqueCheckState
from .rules.types import CriterionResult


class _CritiqueRuleAgent(Protocol):
    penalties: dict[str, float]

    def _create_result(
        self,
        name: str,
        passed: bool,
        issues: list[str],
        severity: str | None = None,
        confidence: float = 1.0,
    ) -> CriterionResult: ...


def evaluate_rule_criteria(
    agent: _CritiqueRuleAgent,
    *,
    text: str,
    context: dict[str, Any],
    criteria: list[str],
    rules: dict[str, Callable[..., CriterionResult]],
) -> CritiqueCheckState:
    """Execute configured rule-backed critique checks and aggregate their output."""
    per_critique: list[CriterionResult] = []
    warnings: list[str] = []
    issues: list[str] = []
    score = 1.0
    for criterion_name in criteria:
        check_fn = rules.get(criterion_name)
        if not check_fn:
            warnings.append(f"Criterion '{criterion_name}' not implemented")
            continue
        try:
            result = check_fn(agent, text, context)
            per_critique.append(result)
            if result.result == "FAIL":
                score -= agent.penalties.get(criterion_name, 0.1)
                issues.extend(result.issues)
        except Exception as exc:
            error_msg = f"Check failed: {exc!s}"
            per_critique.append(
                agent._create_result(
                    criterion_name,
                    False,
                    [error_msg],
                    severity="Critical",
                )
            )
            score -= agent.penalties.get(criterion_name, 0.1)
            issues.append(f"Criterion {criterion_name} failed: {exc!s}")
    return CritiqueCheckState(score, per_critique, warnings, issues)


__all__ = ["evaluate_rule_criteria"]
