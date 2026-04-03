"""Consistency-focused critique rules."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

from .types import CriterionResult

if TYPE_CHECKING:
    from bijux_agent.agents.critique.core import CritiqueAgent


def check_not_empty(
    agent: CritiqueAgent,
    text: str,
    context: dict[str, Any],
) -> CriterionResult:
    return agent._create_result(
        agent.Criteria.NOT_EMPTY,
        bool(text.strip()),
        ["Text is empty"],
    )


def check_no_repetition(
    agent: CritiqueAgent,
    text: str,
    context: dict[str, Any],
) -> CriterionResult:
    words = text.lower().split()
    n = agent.repetition_ngram
    if len(words) >= n:
        ngrams = [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]
        counts = Counter(ngrams)
        most_common = counts.most_common(1)
        if most_common and most_common[0][1] > agent.max_repetition:
            ngram, count = most_common[0]
            return agent._create_result(
                agent.Criteria.NO_REPETITION,
                False,
                [
                    f"Excessive repetition of {n}-gram '{ngram}' "
                    f"({count} times, max {agent.max_repetition})"
                ],
            )

    if context.get("enable_semantic_repetition", False):
        import re

        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        for i in range(len(sentences)):
            for j in range(i + 1, len(sentences)):
                s1_words = set(sentences[i].lower().split())
                s2_words = set(sentences[j].lower().split())
                overlap = len(s1_words.intersection(s2_words))
                overlap /= min(len(s1_words), len(s2_words))
                if overlap > 0.8:
                    return agent._create_result(
                        agent.Criteria.NO_REPETITION,
                        False,
                        [
                            "Semantic repetition detected between sentences: "
                            f"'{sentences[i]}' and '{sentences[j]}'"
                        ],
                    )
    return agent._create_result(agent.Criteria.NO_REPETITION, True, [])


def check_length_reasonable(
    agent: CritiqueAgent,
    text: str,
    context: dict[str, Any],
) -> CriterionResult:
    n_chars = len(text)
    if n_chars < agent.min_length:
        return agent._create_result(
            agent.Criteria.LENGTH_REASONABLE,
            False,
            [f"Text too short ({n_chars} chars, min {agent.min_length})"],
        )
    if n_chars > agent.max_length:
        return agent._create_result(
            agent.Criteria.LENGTH_REASONABLE,
            False,
            [f"Text too long ({n_chars} chars, max {agent.max_length})"],
        )
    return agent._create_result(agent.Criteria.LENGTH_REASONABLE, True, [])


RULES: dict[str, Any] = {
    "not_empty": check_not_empty,
    "no_repetition": check_no_repetition,
    "length_reasonable": check_length_reasonable,
}
