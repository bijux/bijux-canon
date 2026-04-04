from __future__ import annotations

from unittest.mock import Mock

import pytest

from bijux_canon_agent.agents.file_reader.telemetry_events import (
    emit_cache_key_metric,
    flush_agent_logs,
    get_agent_telemetry,
    reset_agent_telemetry,
)


def test_emit_cache_key_metric_records_generation() -> None:
    logger = Mock()
    logger_manager = Mock()

    emit_cache_key_metric("cache-key", logger=logger, logger_manager=logger_manager)

    logger.debug.assert_called_once()
    logger_manager.log_metric.assert_called_once()


def test_flush_agent_logs_records_flush() -> None:
    logger = Mock()
    logger_manager = Mock()

    flush_agent_logs(logger=logger, logger_manager=logger_manager)

    logger_manager.flush.assert_called_once()
    logger_manager.log_metric.assert_called_once()


@pytest.mark.asyncio
async def test_get_agent_telemetry_returns_metrics() -> None:
    logger = Mock()
    logger_manager = Mock()
    logger_manager.get_metrics.return_value = {"requests": {"count": 1}}

    metrics = await get_agent_telemetry(logger=logger, logger_manager=logger_manager)

    assert metrics == {"requests": {"count": 1}}
    logger.debug.assert_called_once()


def test_reset_agent_telemetry_resets_metrics() -> None:
    logger = Mock()
    logger_manager = Mock()

    reset_agent_telemetry(logger=logger, logger_manager=logger_manager)

    logger_manager.reset_metrics.assert_called_once()
    logger_manager.log_metric.assert_called_once()
