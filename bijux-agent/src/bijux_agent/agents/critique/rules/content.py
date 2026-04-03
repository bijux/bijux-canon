"""Content-focused critique rules."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from .types import CriterionResult

if TYPE_CHECKING:
    from bijux_agent.agents.critique.core import CritiqueAgent


def check_no_hallucination(
    agent: CritiqueAgent,
    text: str,
    context: dict[str, Any],
) -> CriterionResult:
    source_text = context.get("source_text", context.get("text", ""))
    if not source_text:
        return agent._create_result(
            agent.Criteria.NO_HALLUCINATION,
            True,
            [],
            confidence=0.5,
        )

    patterns = ["completely unrelated", "as an ai language model", "i am not"]
    for pattern in patterns:
        if pattern in text.lower():
            return agent._create_result(
                agent.Criteria.NO_HALLUCINATION,
                False,
                [f"Potential hallucination detected: '{pattern}'"],
            )

    sentences = re.split(r"[.!?]+", text)
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        words = set(sentence.lower().split())
        if not words:
            continue
        source_words = set(source_text.lower().split())
        overlap = len(words.intersection(source_words)) / len(words)
        if overlap < 0.3:
            return agent._create_result(
                agent.Criteria.NO_HALLUCINATION,
                False,
                [
                    f"Potential hallucination: '{sentence}' has low overlap "
                    f"with source ({overlap:.2f})"
                ],
                confidence=0.7,
            )

    return agent._create_result(agent.Criteria.NO_HALLUCINATION, True, [])


def check_no_unsupported_claims(
    agent: CritiqueAgent,
    text: str,
    context: dict[str, Any],
) -> CriterionResult:
    if context.get("require_citations", False) and not re.search(r"\[\d+\]", text):
        return agent._create_result(
            agent.Criteria.NO_UNSUPPORTED,
            False,
            ["Claims detected without citations"],
        )
    return agent._create_result(agent.Criteria.NO_UNSUPPORTED, True, [])


def check_relevance(
    agent: CritiqueAgent,
    text: str,
    context: dict[str, Any],
) -> CriterionResult:
    task_goal_keywords = context.get("task_goal_keywords", [])
    if not task_goal_keywords:
        return agent._create_result(
            agent.Criteria.RELEVANCE,
            True,
            [],
            confidence=0.5,
        )

    required_topics = {
        "henan_projects": ["henan", "wind", "solar"],
        "thermal_power": ["thermal power", "14th five-year plan", "retrofitting"],
        "industry_trends": ["industry trends", "company updates"],
    }

    missing_topics: list[str] = []
    text_lower = text.lower()
    for topic, keywords in required_topics.items():
        topic_covered = any(keyword in text_lower for keyword in keywords)
        if not topic_covered:
            missing_topics.append(topic)

    if missing_topics:
        return agent._create_result(
            agent.Criteria.RELEVANCE,
            False,
            [f"Missing required topics: {', '.join(missing_topics)}"],
            confidence=0.9,
        )

    keyword_coverage = sum(
        1 for keyword in task_goal_keywords if keyword.lower() in text_lower
    )
    coverage_ratio = (
        keyword_coverage / len(task_goal_keywords) if task_goal_keywords else 1.0
    )
    if coverage_ratio < 0.5:
        return agent._create_result(
            agent.Criteria.RELEVANCE,
            False,
            [
                f"Low keyword coverage ({coverage_ratio:.2f}): Only "
                f"{keyword_coverage}/{len(task_goal_keywords)} keywords present"
            ],
            confidence=0.8,
        )

    return agent._create_result(agent.Criteria.RELEVANCE, True, [], confidence=0.95)


RULES: dict[str, Any] = {
    "no_hallucination": check_no_hallucination,
    "no_unsupported": check_no_unsupported_claims,
    "relevance": check_relevance,
}
