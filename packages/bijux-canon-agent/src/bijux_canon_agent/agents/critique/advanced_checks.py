"""Advanced critique check helpers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from bijux_canon_agent.observability.logging import CustomLogger

from .rules.types import CriterionResult, CritiqueSeverity

LLMCritiqueFn = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]
CustomChecksFn = Callable[[str, dict[str, Any]], Awaitable[list[str] | None]]


@dataclass
class CritiqueCheckState:
    """Mutable state carried through advanced critique checks."""

    score: float
    per_critique: list[CriterionResult]
    warnings: list[str]
    issues: list[str]


async def run_advanced_checks(
    *,
    state: CritiqueCheckState,
    text: str,
    context: dict[str, Any],
    criteria: list[str],
    penalties: dict[str, float],
    suggestion_map: dict[str, str],
    severity_map: dict[str, str],
    llm_critique_fn: LLMCritiqueFn | None,
    custom_checks: CustomChecksFn | None,
    max_retries: int,
    logger: CustomLogger,
    no_hallucination_name: str,
    no_unsupported_name: str,
) -> CritiqueCheckState:
    """Run advanced critique checks and mutate the provided state."""
    await _run_llm_checks(
        state=state,
        text=text,
        context=context,
        criteria=criteria,
        penalties=penalties,
        suggestion_map=suggestion_map,
        severity_map=severity_map,
        llm_critique_fn=llm_critique_fn,
        max_retries=max_retries,
        logger=logger,
        llm_criteria=[no_hallucination_name, no_unsupported_name],
    )
    await _run_custom_checks(
        state=state,
        text=text,
        context=context,
        custom_checks=custom_checks,
        max_retries=max_retries,
        logger=logger,
    )
    return state


async def _run_llm_checks(
    *,
    state: CritiqueCheckState,
    text: str,
    context: dict[str, Any],
    criteria: list[str],
    penalties: dict[str, float],
    suggestion_map: dict[str, str],
    severity_map: dict[str, str],
    llm_critique_fn: LLMCritiqueFn | None,
    max_retries: int,
    logger: CustomLogger,
    llm_criteria: list[str],
) -> None:
    """Run retrying LLM-backed critique checks."""
    if llm_critique_fn is None:
        return
    for criterion in llm_criteria:
        if criterion not in criteria:
            continue
        llm_result = await _run_llm_check_with_retries(
            llm_critique_fn=llm_critique_fn,
            text=text,
            context=context,
            criterion=criterion,
            max_retries=max_retries,
            logger=logger,
        )
        if llm_result is None:
            state.warnings.append(
                f"LLM critique for '{criterion}' failed after retries"
            )
            continue
        if llm_result.get("result") == "FAIL":
            state.score -= penalties.get(criterion, 0.3)
            llm_issues = list(llm_result.get("issues", []))
            state.per_critique.append(
                CriterionResult(
                    name=criterion,
                    result="FAIL",
                    issues=llm_issues,
                    suggestion=suggestion_map[criterion],
                    severity=severity_map[criterion],
                    confidence=llm_result.get("confidence", 1.0),
                )
            )
            state.issues.extend(llm_issues)
        confidence = float(llm_result.get("confidence", 1.0))
        if confidence < 0.7:
            state.warnings.append(
                f"Low confidence for LLM check '{criterion}': {confidence}"
            )


async def _run_llm_check_with_retries(
    *,
    llm_critique_fn: LLMCritiqueFn,
    text: str,
    context: dict[str, Any],
    criterion: str,
    max_retries: int,
    logger: CustomLogger,
) -> dict[str, Any] | None:
    """Run one LLM-backed critique check until success or retry exhaustion."""
    for attempt in range(max_retries + 1):
        try:
            return await llm_critique_fn(text, {**context, "check": criterion})
        except Exception as exc:
            logger.error(
                f"LLM critique for '{criterion}' attempt "
                f"{attempt + 1}/{max_retries + 1} failed: {exc!s}",
                extra={"context": {"stage": "llm_critique"}},
            )
    return None


async def _run_custom_checks(
    *,
    state: CritiqueCheckState,
    text: str,
    context: dict[str, Any],
    custom_checks: CustomChecksFn | None,
    max_retries: int,
    logger: CustomLogger,
) -> None:
    """Run custom critique checks with retry handling."""
    if custom_checks is None:
        return
    custom_issues = await _run_custom_checks_with_retries(
        custom_checks=custom_checks,
        text=text,
        context=context,
        max_retries=max_retries,
        logger=logger,
    )
    if custom_issues is None:
        state.warnings.append("Custom checks failed after retries")
        return
    if not custom_issues:
        return
    state.issues.extend(custom_issues)
    state.per_critique.append(
        CriterionResult(
            name="custom",
            result="FAIL",
            issues=custom_issues,
            suggestion="Resolve user-defined issues.",
            severity=CritiqueSeverity.MAJOR.value,
        )
    )
    state.score -= 0.2


async def _run_custom_checks_with_retries(
    *,
    custom_checks: CustomChecksFn,
    text: str,
    context: dict[str, Any],
    max_retries: int,
    logger: CustomLogger,
) -> list[str] | None:
    """Run custom checks until success or retry exhaustion."""
    for attempt in range(max_retries + 1):
        try:
            return list(await custom_checks(text, context) or [])
        except Exception as exc:
            logger.error(
                f"Custom checks attempt {attempt + 1}/{max_retries + 1} "
                f"failed: {exc!s}",
                extra={"context": {"stage": "custom_checks"}},
            )
    return None
