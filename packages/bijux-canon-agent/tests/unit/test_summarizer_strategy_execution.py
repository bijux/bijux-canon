from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from bijux_canon_agent.agents.summarizer.strategy_execution import run_summary_strategy


class _Logger:
    def debug(self, *_args: object, **_kwargs: object) -> None:
        return None


class _Agent:
    STRATEGY_EXTRACTIVE = "extractive"
    STRATEGY_ABSTRACTIVE = "abstractive"

    def __init__(self, *, strategy: str, backend: str = "simple") -> None:
        self.strategy = strategy
        self.backend = backend
        self.logger = _Logger()


@pytest.mark.asyncio
async def test_run_summary_strategy_uses_extractive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parse_sections = AsyncMock()
    parse_sections.side_effect = AssertionError("should not await parse_sections")
    monkeypatch.setattr(
        "bijux_canon_agent.agents.summarizer.strategy_execution.extractive.parse_sections",
        lambda *_args, **_kwargs: [{"heading": "One", "content": "A"}],
    )
    monkeypatch.setattr(
        "bijux_canon_agent.agents.summarizer.strategy_execution.extractive.generate_extractive_summary",
        lambda *_args, **_kwargs: "extractive-summary",
    )

    summary, method = await run_summary_strategy(
        _Agent(strategy="extractive"),
        text="Body",
        prompt_prefix="",
        task_goal="Summarize",
        keywords=["body"],
    )

    assert summary == "extractive-summary"
    assert method == "extractive_simple"


@pytest.mark.asyncio
async def test_run_summary_strategy_uses_abstractive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "bijux_canon_agent.agents.summarizer.strategy_execution.extractive.parse_sections",
        lambda *_args, **_kwargs: [{"heading": "One", "content": "A"}],
    )
    monkeypatch.setattr(
        "bijux_canon_agent.agents.summarizer.strategy_execution.abstractive.generate_abstractive_summary",
        AsyncMock(return_value="abstractive-summary"),
    )

    summary, method = await run_summary_strategy(
        _Agent(strategy="abstractive", backend="llm"),
        text="Body",
        prompt_prefix="Revise",
        task_goal="Summarize",
        keywords=["body"],
    )

    assert summary == "abstractive-summary"
    assert method == "abstractive_llm"


@pytest.mark.asyncio
async def test_run_summary_strategy_combines_hybrid_outputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "bijux_canon_agent.agents.summarizer.strategy_execution.extractive.parse_sections",
        lambda *_args, **_kwargs: [{"heading": "One", "content": "A"}],
    )
    monkeypatch.setattr(
        "bijux_canon_agent.agents.summarizer.strategy_execution.extractive.generate_extractive_summary",
        lambda *_args, **_kwargs: "extractive-summary",
    )
    monkeypatch.setattr(
        "bijux_canon_agent.agents.summarizer.strategy_execution.abstractive.generate_abstractive_summary",
        AsyncMock(return_value="abstractive-summary"),
    )
    monkeypatch.setattr(
        "bijux_canon_agent.agents.summarizer.strategy_execution.postprocessing.combine_summaries",
        lambda *_args, **_kwargs: "hybrid-summary",
    )

    summary, method = await run_summary_strategy(
        _Agent(strategy="hybrid", backend="llm"),
        text="Body",
        prompt_prefix="Revise",
        task_goal="Summarize",
        keywords=["body"],
    )

    assert summary == "hybrid-summary"
    assert method == "hybrid_llm"
