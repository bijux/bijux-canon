from __future__ import annotations

from unittest.mock import Mock

from bijux_canon_agent.agents.file_reader.read_request import build_file_read_request


def test_build_file_read_request_resolves_path_and_suffix() -> None:
    request = build_file_read_request(
        context={"file_path": "/tmp/sample.PDF"},
        cache_key="cache-key",
        logger=Mock(),
        logger_manager=Mock(),
    )

    assert request is not None
    assert request.file_path == "/tmp/sample.PDF"
    assert request.file_suffix == "pdf"
    assert request.cache_key == "cache-key"


def test_build_file_read_request_returns_none_without_path() -> None:
    logger = Mock()
    logger_manager = Mock()

    request = build_file_read_request(
        context={},
        cache_key="cache-key",
        logger=logger,
        logger_manager=logger_manager,
    )

    assert request is None
    logger.error.assert_called_once()
    logger_manager.log_metric.assert_called_once()
