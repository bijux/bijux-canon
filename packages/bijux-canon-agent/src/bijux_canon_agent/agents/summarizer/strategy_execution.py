"""Strategy execution helpers for the summarizer agent."""

from __future__ import annotations

from typing import Any, Protocol

from .rules import (
    abstractive,
    extractive,
    postprocessing,
)


class _SummaryStrategyAgent(Protocol):
    strategy: str
    backend: str
    STRATEGY_EXTRACTIVE: str
    STRATEGY_ABSTRACTIVE: str
    logger: Any


async def run_summary_strategy(
    agent: _SummaryStrategyAgent,
    *,
    text: str,
    prompt_prefix: str,
    task_goal: str,
    keywords: list[str],
) -> tuple[str, str]:
    """Execute the configured summary strategy and return the rendered summary."""
    method = f"{agent.strategy}_{agent.backend}"
    sections = extractive.parse_sections(agent, text, keywords)
    agent.logger.debug(
        f"Parsed {len(sections)} sections",
        extra={"context": {"sections": [section["heading"] for section in sections]}},
    )

    if agent.strategy == agent.STRATEGY_EXTRACTIVE:
        summary = extractive.generate_extractive_summary(agent, sections, keywords)
    elif agent.strategy == agent.STRATEGY_ABSTRACTIVE:
        summary = await abstractive.generate_abstractive_summary(
            agent, sections, prompt_prefix, task_goal, keywords
        )
    else:
        summary = await _run_hybrid_summary(
            agent,
            sections=sections,
            prompt_prefix=prompt_prefix,
            task_goal=task_goal,
            keywords=keywords,
        )

    agent.logger.debug(
        "Summarization strategy applied",
        extra={
            "context": {
                "strategy": agent.strategy,
                "method": method,
                "summary_length": len(summary),
            }
        },
    )
    return summary, method


async def _run_hybrid_summary(
    agent: _SummaryStrategyAgent,
    *,
    sections: list[dict[str, Any]],
    prompt_prefix: str,
    task_goal: str,
    keywords: list[str],
) -> str:
    extractive_summary = extractive.generate_extractive_summary(
        agent, sections, keywords
    )
    abstractive_summary = await abstractive.generate_abstractive_summary(
        agent, sections, prompt_prefix, task_goal, keywords
    )
    return postprocessing.combine_summaries(
        agent, extractive_summary, abstractive_summary
    )


__all__ = ["run_summary_strategy"]
