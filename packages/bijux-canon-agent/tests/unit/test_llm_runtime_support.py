from __future__ import annotations

from aiohttp import ClientTimeout
from bijux_canon_agent.llm.llm_runtime import LLMBackend, LLMResponse
from bijux_canon_agent.llm.runtime_support import (
    execute_backend_attempt,
    retry_backoff,
)
import pytest


class _BackendStub(LLMBackend):
    async def generate(self, prompt, max_tokens, session):  # type: ignore[override]
        del max_tokens, session
        return LLMResponse(content=f"echo:{prompt}", metadata={})


@pytest.mark.asyncio
async def test_execute_backend_attempt_returns_response(logger_manager) -> None:
    response, duration = await execute_backend_attempt(
        backend=_BackendStub(),
        timeout=ClientTimeout(total=1),
        prompt="hello",
        max_tokens=None,
        backend_name="stub",
        logger_manager=logger_manager,
    )

    assert response.content == "echo:hello"
    assert duration >= 0


def test_retry_backoff_uses_exponential_growth() -> None:
    assert retry_backoff(0.5, 1) == 0.5
    assert retry_backoff(0.5, 3) == 2.0
