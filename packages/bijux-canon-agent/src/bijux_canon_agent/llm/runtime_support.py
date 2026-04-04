"""Support helpers for LLM runtime transport and retry handling."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

import aiohttp
from aiohttp import ClientTimeout

from bijux_canon_agent.observability.logging import MetricType

if TYPE_CHECKING:
    from bijux_canon_agent.llm.llm_runtime import LLMBackend, LLMResponse


async def execute_backend_attempt(
    *,
    backend: LLMBackend,
    timeout: ClientTimeout,
    prompt: str,
    max_tokens: int | None,
    backend_name: str,
    logger_manager: Any,
) -> tuple[LLMResponse, float]:
    """Execute one backend request and record its latency."""
    async with aiohttp.ClientSession(timeout=timeout) as session:
        start_time = time.time()
        response = await backend.generate(prompt, max_tokens, session)
        duration = time.time() - start_time
    logger_manager.log_metric(
        "llm_request_duration",
        duration,
        MetricType.HISTOGRAM,
        tags={"backend": backend_name},
    )
    return response, duration


async def handle_failed_attempt(
    *,
    attempt: int,
    duration: float,
    error: str,
    max_retries: int,
    retry_delay: float,
    backend_name: str,
    logger: Any,
    logger_manager: Any,
) -> None:
    """Record a failed attempt and either sleep or raise on exhaustion."""
    logger.warning(
        f"LLM generation failed: {error}",
        extra={"context": {"attempt": attempt, "duration": duration}},
    )
    logger_manager.log_metric(
        "llm_request_errors",
        1,
        MetricType.COUNTER,
        tags={"backend": backend_name, "attempt": str(attempt)},
    )
    if attempt == max_retries:
        raise Exception(f"All retries failed: {error}")
    await asyncio.sleep(retry_backoff(retry_delay, attempt))


def record_generation_success(
    *,
    duration: float,
    response: LLMResponse,
    backend_name: str,
    logger: Any,
    logger_manager: Any,
) -> None:
    """Record successful LLM generation telemetry."""
    logger_manager.log_metric(
        "llm_requests",
        1,
        MetricType.COUNTER,
        tags={"backend": backend_name, "status": "success"},
    )
    logger.info(
        "LLM generation completed",
        extra={
            "context": {
                "stage": "completion",
                "duration": duration,
                "response_length": len(response.content),
            }
        },
    )


def retry_backoff(retry_delay: float, attempt: int) -> float:
    """Calculate exponential backoff for an LLM retry."""
    return float(retry_delay) * float(2 ** (attempt - 1))
