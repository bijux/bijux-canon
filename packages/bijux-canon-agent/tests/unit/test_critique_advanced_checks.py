from __future__ import annotations

from bijux_canon_agent.agents.critique.advanced_checks import (
    CritiqueCheckState,
    run_advanced_checks,
)
import pytest


@pytest.mark.asyncio
async def test_run_advanced_checks_records_llm_failures(logger_manager) -> None:
    async def llm_critique_fn(
        _text: str,
        _context: dict[str, object],
    ) -> dict[str, object]:
        return {
            "result": "FAIL",
            "issues": ["Unsupported claim"],
            "confidence": 0.95,
        }

    state = CritiqueCheckState(1.0, [], [], [])
    updated = await run_advanced_checks(
        state=state,
        text="summary",
        context={},
        criteria=["no_unsupported_claims"],
        penalties={"no_unsupported_claims": 0.2},
        suggestion_map={"no_unsupported_claims": "Add support."},
        severity_map={"no_unsupported_claims": "Major"},
        llm_critique_fn=llm_critique_fn,
        custom_checks=None,
        max_retries=1,
        logger=logger_manager.get_logger(),
        no_hallucination_name="no_hallucination",
        no_unsupported_name="no_unsupported_claims",
    )

    assert updated.score == 0.8
    assert updated.issues == ["Unsupported claim"]
    assert updated.per_critique[0].name == "no_unsupported_claims"


@pytest.mark.asyncio
async def test_run_advanced_checks_records_custom_issues(logger_manager) -> None:
    async def custom_checks(
        _text: str,
        _context: dict[str, object],
    ) -> list[str]:
        return ["Missing section"]

    updated = await run_advanced_checks(
        state=CritiqueCheckState(1.0, [], [], []),
        text="summary",
        context={},
        criteria=[],
        penalties={},
        suggestion_map={},
        severity_map={},
        llm_critique_fn=None,
        custom_checks=custom_checks,
        max_retries=1,
        logger=logger_manager.get_logger(),
        no_hallucination_name="no_hallucination",
        no_unsupported_name="no_unsupported_claims",
    )

    assert updated.score == 0.8
    assert updated.issues == ["Missing section"]
    assert updated.per_critique[0].name == "custom"
