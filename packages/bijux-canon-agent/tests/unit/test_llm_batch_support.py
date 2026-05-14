from __future__ import annotations

from unittest.mock import Mock

import pytest

from bijux_canon_agent.llm.batch_support import (
    collect_batch_responses,
    execute_batch_requests,
)


@pytest.mark.asyncio
async def test_execute_batch_requests_preserves_result_order() -> None:
    async def _generate(prompt: str, max_tokens: int | None) -> str:
        _ = max_tokens
        return prompt.upper()

    results = await execute_batch_requests(
        prompts=["a", "b"],
        max_tokens=12,
        generate=_generate,
    )

    assert results == ["A", "B"]


def test_collect_batch_responses_records_failures() -> None:
    logger = Mock()
    logger_manager = Mock()

    responses = collect_batch_responses(
        results=["ok", RuntimeError("boom")],
        backend_name="deepseek",
        logger=logger,
        logger_manager=logger_manager,
    )

    assert responses == ["ok", ""]
    logger.error.assert_called_once()
    logger_manager.log_metric.assert_called_once()
