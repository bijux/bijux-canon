"""Result-shaping helpers for the critique agent."""

from __future__ import annotations

import time
from typing import Any

from .rules.types import CriterionResult, CritiqueResult


def build_critique_output(
    result: CritiqueResult,
    summary: str,
    source_text: str,
    *,
    criteria: Any,
) -> dict[str, Any]:
    """Format the critique output with detailed scores and feedback."""
    scores = {
        "accuracy": 5,
        "completeness": 5,
        "clarity": 5,
        "brevity": 5,
        "critical_tone": 5,
        "relevance": 5,
    }
    strengths: list[str] = []
    weaknesses: list[str] = []
    overall_score = int(result["score"] * 5)
    for key in scores:
        scores[key] = overall_score

    for crit in result["per_criterion"]:
        crit_name = crit["name"]
        if crit["result"] == "PASS":
            strengths.append(
                f"Criterion '{crit_name}' passed: Meets expectations "
                f"(Confidence: {crit['confidence']})."
            )
            continue

        if crit_name == criteria.NO_HALLUCINATION and source_text:
            issue_text = crit["issues"][0].lower()
            if not any(word in source_text.lower() for word in issue_text.split()):
                weaknesses.append(
                    f"Hallucination: '{issue_text}' not in source "
                    f"(Confidence: {crit['confidence']})."
                )
            else:
                weaknesses.append(
                    f"Criterion '{crit_name}' failed: {crit['issues'][0]} "
                    f"(Confidence: {crit['confidence']})."
                )
        elif crit_name == criteria.RELEVANCE:
            weaknesses.append(
                f"Relevance issue: {crit['issues'][0]} "
                f"(Confidence: {crit['confidence']})."
            )
        else:
            weaknesses.append(
                f"Criterion '{crit_name}' failed: {crit['issues'][0]} "
                f"(Confidence: {crit['confidence']})."
            )

        _adjust_scores(criteria, crit_name, scores)

    for key in scores:
        scores[key] = max(0, min(5, scores[key]))

    return _finalize_critique_output(
        result,
        scores=scores,
        strengths=strengths,
        weaknesses=weaknesses,
        criteria=criteria,
    )


def create_criterion_result(
    name: str,
    passed: bool,
    issues: list[str],
    *,
    suggestion_map: dict[str, str],
    severity_map: dict[str, str],
    severity: str | None = None,
    confidence: float = 1.0,
) -> CriterionResult:
    """Create a criterion result with configured suggestion and severity maps."""
    return CriterionResult(
        name=name,
        result="PASS" if passed else "FAIL",
        issues=issues,
        suggestion=suggestion_map[name] if not passed else "",
        severity=severity or severity_map[name] if not passed else "",
        confidence=confidence,
    )


async def build_final_report(
    status: str,
    score: float,
    per_critique: list[CriterionResult],
    warnings: list[str],
    issues: list[str],
    *,
    criteria: list[str],
    relevance_name: str,
) -> CritiqueResult:
    """Generate the final critique report and ordered action plan."""
    fails = [criterion for criterion in per_critique if criterion.result == "FAIL"]
    fails_sorted = sorted(
        fails,
        key=lambda criterion: {"Critical": 1, "Major": 2, "Minor": 3}.get(
            criterion.severity, 4
        ),
    )
    action_plan = [
        f"{criterion.severity}: {criterion.suggestion} "
        f"(Issue: {', '.join(criterion.issues)}, Confidence: {criterion.confidence})"
        for criterion in fails_sorted
    ]
    for criterion in fails_sorted:
        if criterion.name == relevance_name:
            missing_topics = (
                criterion.issues[0].split(": ")[1]
                if ": " in criterion.issues[0]
                else criterion.issues[0]
            )
            action_plan.append(
                f"Critical: Focus on including details about {missing_topics} "
                "in the summary."
            )

    return {
        "critique_status": status,
        "score": score,
        "per_criterion": [vars(criterion) for criterion in per_critique],
        "warnings": warnings,
        "issues": issues,
        "criteria": criteria,
        "action_plan": action_plan,
        "audit": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "shards_merged": 1,
        },
    }


def build_critique_error_payload(msg: str, criteria: list[str]) -> CritiqueResult:
    """Return a standardized critique error payload."""
    return {
        "critique_status": "failed",
        "score": 0.0,
        "per_criterion": [],
        "warnings": [msg],
        "issues": [msg],
        "criteria": criteria,
        "action_plan": [],
        "audit": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "shards_merged": 1,
        },
    }


def build_critique_schema() -> dict[str, Any]:
    """Describe the critique output schema for validation and composition."""
    return {
        "critique": {
            "scores": dict.fromkeys(
                [
                    "accuracy",
                    "completeness",
                    "clarity",
                    "brevity",
                    "critical_tone",
                    "relevance",
                ],
                "int (0-5)",
            ),
            "strengths": "list[str] (length 2)",
            "weaknesses": "list[str] (length 2)",
            "hallucination_flag": "bool",
            "missing_info_flag": "bool",
            "relevance_flag": "bool",
            "final_quality": "str (OUTSTANDING/GOOD/OK/POOR/FAIL)",
        }
    }


def build_critique_coverage_report() -> dict[str, Any]:
    """Describe critique input and output boundaries."""
    return {
        "consumes": [
            "summary",
            "text",
            "content",
            "source_text",
            "task_goal_keywords",
        ],
        "modifies": [],
        "produces": ["critique"],
    }


def log_critique_completion(
    *,
    logger: Any,
    result: CritiqueResult,
    duration: float,
) -> None:
    """Log critique completion details with consistent structure."""
    logger.info(
        "Critique completed",
        extra={
            "context": {
                "stage": "completion",
                "status": result.get("critique_status", "unknown"),
                "score": result.get("score", 0.0),
                "duration_sec": duration,
                "issues": result.get("issues", []),
                "warnings": result.get("warnings", []),
            }
        },
    )


def _adjust_scores(criteria: Any, crit_name: str, scores: dict[str, int]) -> None:
    if crit_name == criteria.NOT_EMPTY:
        scores["completeness"] -= 2
    elif crit_name == criteria.NO_HALLUCINATION:
        scores["accuracy"] -= 2
    elif crit_name == criteria.NO_REPETITION:
        scores["clarity"] -= 1
    elif crit_name == criteria.LENGTH_REASONABLE:
        scores["brevity"] -= 1
    elif (
        crit_name == criteria.FORMATTING_BASIC
        or crit_name == criteria.PUNCTUATION_EXCESSIVE
    ):
        scores["clarity"] -= 1
    elif crit_name == criteria.NO_UNSUPPORTED:
        scores["critical_tone"] -= 1
    elif crit_name == criteria.RELEVANCE:
        scores["relevance"] -= 2
        scores["completeness"] -= 1


def _finalize_critique_output(
    result: CritiqueResult,
    *,
    scores: dict[str, int],
    strengths: list[str],
    weaknesses: list[str],
    criteria: Any,
) -> dict[str, Any]:
    avg_score = sum(scores.values()) / len(scores)
    final_quality = (
        "OUTSTANDING"
        if avg_score >= 4.5
        else (
            "GOOD"
            if avg_score >= 3.5
            else ("OK" if avg_score >= 2.5 else "POOR" if avg_score >= 1.5 else "FAIL")
        )
    )
    hallucination_flag = any(
        crit["name"] == criteria.NO_HALLUCINATION and crit["result"] == "FAIL"
        for crit in result["per_criterion"]
    )
    missing_info_flag = any(
        crit["name"] == criteria.NOT_EMPTY and crit["result"] == "FAIL"
        for crit in result["per_criterion"]
    )
    relevance_flag = any(
        crit["name"] == criteria.RELEVANCE and crit["result"] == "FAIL"
        for crit in result["per_criterion"]
    )
    if len(strengths) < 2:
        strengths.extend(["No additional strengths identified."] * (2 - len(strengths)))
    if len(weaknesses) < 2:
        weaknesses.extend(
            ["No additional weaknesses identified."] * (2 - len(weaknesses))
        )
    return {
        "critique_status": result["critique_status"],
        "score": result["score"],
        "per_criterion": result["per_criterion"],
        "warnings": result["warnings"],
        "issues": result["issues"],
        "criteria": result["criteria"],
        "action_plan": result["action_plan"],
        "audit": result["audit"],
        "scores": scores,
        "strengths": strengths[:2],
        "weaknesses": weaknesses[:2],
        "hallucination_flag": hallucination_flag,
        "missing_info_flag": missing_info_flag,
        "relevance_flag": relevance_flag,
        "final_quality": final_quality,
    }


__all__ = [
    "build_critique_coverage_report",
    "build_critique_error_payload",
    "build_critique_output",
    "build_critique_schema",
    "build_final_report",
    "create_criterion_result",
    "log_critique_completion",
]
