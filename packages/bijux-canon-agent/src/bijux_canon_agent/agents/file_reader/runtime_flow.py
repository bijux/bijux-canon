"""Retry and cache helpers for file-reader execution."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import time
from typing import Any

from bijux_canon_agent.observability.logging import (
    CustomLogger,
    LoggerManager,
    MetricType,
)

ReadFn = Callable[[str], Awaitable[dict[str, Any]]]
ErrorResultFn = Callable[
    [str, dict[str, Any], str, dict[str, Any]],
    Awaitable[dict[str, Any]],
]


def resolve_file_path(
    context: dict[str, Any],
    *,
    logger: CustomLogger,
    logger_manager: LoggerManager,
) -> str | None:
    """Return the requested file path or record input validation metrics."""
    file_path = context.get("file_path")
    if file_path:
        return str(file_path)
    logger.error(
        "No file_path provided",
        extra={"context": {"stage": "input_validation"}},
    )
    logger_manager.log_metric(
        "input_validation_errors",
        1,
        MetricType.COUNTER,
        tags={"stage": "input_validation"},
    )
    return None


def load_cached_result(
    cache: dict[str, dict[str, Any]] | None,
    cache_key: str,
    *,
    logger: CustomLogger,
    logger_manager: LoggerManager,
) -> dict[str, Any] | None:
    """Return the cached file-read result when present."""
    if cache is None or cache_key not in cache:
        return None
    logger.debug(
        "Cache hit",
        extra={"context": {"stage": "cache_check", "cache_key": cache_key}},
    )
    logger_manager.log_metric(
        "cache_hits",
        1,
        MetricType.COUNTER,
        tags={"stage": "cache_check"},
    )
    return {**cache[cache_key], "cache_hit": True}


def store_cached_result(
    cache: dict[str, dict[str, Any]] | None,
    cache_key: str,
    read_result: dict[str, Any],
    *,
    logger: CustomLogger,
    logger_manager: LoggerManager,
) -> None:
    """Persist a read result in cache when caching is enabled."""
    if cache is None:
        return
    cache[cache_key] = read_result
    logger.debug("Cached result", extra={"context": {"cache_key": cache_key}})
    logger_manager.log_metric(
        "cache_stores",
        1,
        MetricType.COUNTER,
        tags={"stage": "cache_store"},
    )


async def read_with_retries(
    *,
    context: dict[str, Any],
    file_path: str,
    file_suffix: str,
    custom_readers: dict[str, ReadFn],
    default_reader: ReadFn,
    max_retries: int,
    backoff_strategy: str,
    logger: CustomLogger,
    logger_manager: LoggerManager,
    error_result: ErrorResultFn,
) -> dict[str, Any]:
    """Read a file using retry/backoff semantics and standardized telemetry."""
    reader = custom_readers.get(file_suffix, default_reader)
    read_result: dict[str, Any] = {}
    for attempt in range(1, max_retries + 1):
        try:
            start = time.perf_counter()
            read_result = await reader(file_path)
            duration = time.perf_counter() - start
            read_result["read_duration_sec"] = round(duration, 4)
            read_result["attempt"] = attempt
            _record_read_success(
                duration=duration,
                attempt=attempt,
                file_suffix=file_suffix,
                logger=logger,
                logger_manager=logger_manager,
            )
            if "error" not in read_result or not read_result["error"]:
                return read_result
        except Exception as exc:
            read_result = await _handle_read_failure(
                exc=exc,
                attempt=attempt,
                context=context,
                file_suffix=file_suffix,
                logger=logger,
                logger_manager=logger_manager,
                error_result=error_result,
            )
        if attempt < max_retries:
            await _sleep_for_retry(
                attempt=attempt,
                backoff_strategy=backoff_strategy,
                logger=logger,
            )
    return read_result


def calculate_backoff(backoff_strategy: str, attempt: int) -> float:
    """Calculate the retry backoff for the configured strategy."""
    if backoff_strategy == "exponential":
        return 0.5 * (2 ** (attempt - 1))
    return 0.5 * attempt


def _record_read_success(
    *,
    duration: float,
    attempt: int,
    file_suffix: str,
    logger: CustomLogger,
    logger_manager: LoggerManager,
) -> None:
    """Record successful file-read telemetry and debug logs."""
    logger_manager.log_metric(
        "file_read_duration",
        duration,
        MetricType.HISTOGRAM,
        tags={
            "stage": "file_read",
            "attempt": str(attempt),
            "file_type": file_suffix,
        },
    )
    logger.debug(
        "File read successful",
        extra={
            "context": {
                "stage": "file_read",
                "attempt": attempt,
                "duration": duration,
                "file_type": file_suffix,
            }
        },
    )


async def _handle_read_failure(
    *,
    exc: Exception,
    attempt: int,
    context: dict[str, Any],
    file_suffix: str,
    logger: CustomLogger,
    logger_manager: LoggerManager,
    error_result: ErrorResultFn,
) -> dict[str, Any]:
    """Record file-read failure telemetry and return a standard error payload."""
    logger.error(
        f"Read failed on attempt {attempt}: {exc!s}",
        extra={
            "context": {
                "stage": "file_read",
                "attempt": attempt,
                "error": str(exc),
                "file_type": file_suffix,
            }
        },
    )
    logger_manager.log_metric(
        "file_read_errors",
        1,
        MetricType.COUNTER,
        tags={
            "stage": "file_read",
            "attempt": str(attempt),
            "file_type": file_suffix,
        },
    )
    return await error_result(str(exc), context, "file_read", {"attempt": attempt})


async def _sleep_for_retry(
    *,
    attempt: int,
    backoff_strategy: str,
    logger: CustomLogger,
) -> None:
    """Sleep for the configured retry backoff and record the retry event."""
    backoff_delay = calculate_backoff(backoff_strategy, attempt)
    await asyncio.sleep(backoff_delay)
    logger.debug(
        "Retrying after backoff",
        extra={
            "context": {
                "stage": "retry",
                "attempt": attempt,
                "backoff_delay": backoff_delay,
            }
        },
    )
