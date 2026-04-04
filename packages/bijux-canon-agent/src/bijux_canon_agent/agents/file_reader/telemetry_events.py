"""Telemetry control helpers for the file reader agent."""

from __future__ import annotations

from typing import Any

from bijux_canon_agent.observability.logging import LoggerManager, MetricType


def emit_cache_key_metric(
    cache_key: str,
    *,
    logger: Any,
    logger_manager: LoggerManager,
) -> None:
    """Record cache-key generation telemetry with consistent logging."""
    logger.debug(
        "Generated cache key",
        extra={"context": {"stage": "cache_key_generation", "cache_key": cache_key}},
    )
    logger_manager.log_metric(
        "cache_key_generated",
        1,
        MetricType.COUNTER,
        tags={"stage": "cache_key_generation"},
    )


def flush_agent_logs(*, logger: Any, logger_manager: LoggerManager) -> None:
    """Flush file reader logs and record the flush metric."""
    try:
        logger_manager.flush()
        logger.debug("Logs flushed", extra={"context": {"stage": "log_flush"}})
        logger_manager.log_metric(
            "log_flush",
            1,
            MetricType.COUNTER,
            tags={"stage": "log_flush"},
        )
    except Exception as exc:
        logger.error(
            f"Failed to flush logs: {exc!s}",
            extra={"context": {"stage": "log_flush", "error": str(exc)}},
        )


async def get_agent_telemetry(
    *,
    logger: Any,
    logger_manager: LoggerManager,
) -> dict[str, dict[str, Any]]:
    """Retrieve file reader telemetry with consistent debug/error logging."""
    try:
        metrics = logger_manager.get_metrics()
        logger.debug(
            "Telemetry metrics retrieved",
            extra={
                "context": {
                    "stage": "telemetry",
                    "metric_names": list(metrics.keys()),
                }
            },
        )
        logger_manager.log_metric(
            "telemetry_retrieved",
            1,
            MetricType.COUNTER,
            tags={"stage": "telemetry"},
        )
        return metrics
    except Exception as exc:
        logger.error(
            f"Failed to retrieve telemetry: {exc!s}",
            extra={"context": {"stage": "telemetry", "error": str(exc)}},
        )
        return {}


def reset_agent_telemetry(*, logger: Any, logger_manager: LoggerManager) -> None:
    """Reset file reader telemetry with consistent debug/error logging."""
    try:
        logger_manager.reset_metrics()
        logger.debug(
            "Telemetry metrics reset",
            extra={"context": {"stage": "reset_telemetry"}},
        )
        logger_manager.log_metric(
            "metrics_reset",
            1,
            MetricType.COUNTER,
            tags={"stage": "reset_telemetry"},
        )
    except Exception as exc:
        logger.error(
            f"Failed to reset telemetry: {exc!s}",
            extra={"context": {"stage": "reset_telemetry", "error": str(exc)}},
        )


__all__ = [
    "emit_cache_key_metric",
    "flush_agent_logs",
    "get_agent_telemetry",
    "reset_agent_telemetry",
]
