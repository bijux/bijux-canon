"""Batch scheduling helpers for LLM runtime operations."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from bijux_canon_agent.observability.logging import MetricType

GenerateFn = Callable[[str, int | None], Awaitable[str]]


async def execute_batch_requests(
    *,
    prompts: list[str],
    max_tokens: int | None,
    generate: GenerateFn,
) -> list[str | BaseException]:
    """Run LLM generation concurrently for a batch of prompts."""
    tasks = [generate(prompt, max_tokens) for prompt in prompts]
    return await asyncio.gather(*tasks, return_exceptions=True)


def collect_batch_responses(
    *,
    results: list[str | BaseException],
    backend_name: str,
    logger: Any,
    logger_manager: Any,
) -> list[str]:
    """Normalize batch generation results and emit failure telemetry."""
    responses: list[str] = []
    for idx, result in enumerate(results):
        if isinstance(result, BaseException):
            logger.error(f"Batch generation failed for prompt {idx}: {result!s}")
            responses.append("")
            logger_manager.log_metric(
                "llm_batch_errors",
                1,
                MetricType.COUNTER,
                tags={"backend": backend_name, "prompt_idx": str(idx)},
            )
        else:
            responses.append(result)
    return responses


__all__ = ["collect_batch_responses", "execute_batch_requests"]
