from __future__ import annotations

import pytest

from bijux_canon_agent.agents.file_reader.runtime_flow import (
    calculate_backoff,
    load_cached_result,
    read_with_retries,
    resolve_file_path,
    store_cached_result,
)


def test_resolve_file_path_reads_context_value(logger_manager) -> None:
    resolved = resolve_file_path(
        {"file_path": "note.txt"},
        logger=logger_manager.get_logger(),
        logger_manager=logger_manager,
    )

    assert resolved == "note.txt"


def test_cache_helpers_round_trip_results(logger_manager) -> None:
    logger = logger_manager.get_logger()
    cache: dict[str, dict[str, object]] = {}

    store_cached_result(
        cache,
        "abc",
        {"text": "hello"},
        logger=logger,
        logger_manager=logger_manager,
    )
    cached = load_cached_result(
        cache,
        "abc",
        logger=logger,
        logger_manager=logger_manager,
    )

    assert cached == {"text": "hello", "cache_hit": True}


@pytest.mark.asyncio
async def test_read_with_retries_retries_after_failure(logger_manager) -> None:
    attempts = 0

    async def flaky_reader(_file_path: str) -> dict[str, object]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("boom")
        return {"text": "hello"}

    async def error_result(
        msg: str,
        context: dict[str, object],
        stage: str,
        extra: dict[str, object],
    ) -> dict[str, object]:
        return {"error": msg, "context": context, "stage": stage, "extra": extra}

    result = await read_with_retries(
        context={"file_path": "note.txt"},
        file_path="note.txt",
        file_suffix="txt",
        custom_readers={},
        default_reader=flaky_reader,
        max_retries=2,
        backoff_strategy="linear",
        logger=logger_manager.get_logger(),
        logger_manager=logger_manager,
        error_result=error_result,
    )

    assert attempts == 2
    assert result["text"] == "hello"
    assert result["attempt"] == 2


def test_calculate_backoff_supports_linear_and_exponential() -> None:
    assert calculate_backoff("linear", 3) == 1.5
    assert calculate_backoff("exponential", 3) == 2.0
