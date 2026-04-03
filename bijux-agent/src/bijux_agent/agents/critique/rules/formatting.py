"""Formatting-focused critique rules."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from .types import CriterionResult

if TYPE_CHECKING:
    from bijux_agent.agents.critique.core import CritiqueAgent


def check_formatting_basic(
    agent: CritiqueAgent,
    text: str,
    context: dict[str, Any],
) -> CriterionResult:
    issues: list[str] = []
    if "\n\n\n" in text:
        issues.append("Excessive newlines detected")
    if "  " in text:
        issues.append("Multiple consecutive spaces detected")
    if "??" in text or "!!" in text:
        issues.append("Repeated punctuation marks detected")
    return agent._create_result(agent.Criteria.FORMATTING_BASIC, not issues, issues)


def check_punctuation_excessive(
    agent: CritiqueAgent,
    text: str,
    context: dict[str, Any],
) -> CriterionResult:
    if re.search(r"[!?.]{3,}", text):
        return agent._create_result(
            agent.Criteria.PUNCTUATION_EXCESSIVE,
            False,
            ["Excessive punctuation detected (e.g., '...', '!!!')"],
        )
    return agent._create_result(agent.Criteria.PUNCTUATION_EXCESSIVE, True, [])


def check_code_syntax(
    agent: CritiqueAgent,
    text: str,
    context: dict[str, Any],
) -> CriterionResult:
    if "def " in text and not re.search(r"def \w+\(.*\):", text):
        return agent._create_result(
            agent.Criteria.CODE_SYNTAX,
            False,
            ["Invalid function definition detected"],
        )
    if "for " in text and not re.search(r"for \w+ in .+:", text):
        return agent._create_result(
            agent.Criteria.CODE_SYNTAX,
            False,
            ["Invalid for-loop syntax detected"],
        )
    return agent._create_result(agent.Criteria.CODE_SYNTAX, True, [])


RULES: dict[str, Any] = {
    "formatting_basic": check_formatting_basic,
    "punctuation_excessive": check_punctuation_excessive,
    "code_syntax": check_code_syntax,
}
