"""Logger manager module with structured logging, async support, and telemetry."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
import logging
from logging import (
    Handler,
    Logger,
    LogRecord,
    getLevelName,
)
from pathlib import Path
from typing import Any

from bijux_canon_agent.observability.log_handlers import (
    LoggerConfig,
    LoggerSettings,
    contextual_log_records,
    install_custom_log_record_factory,
)
from bijux_canon_agent.observability.log_metrics import LoggerTelemetry, MetricType

install_custom_log_record_factory()


class CustomLogger:
    """Custom logger wrapper exposing context and async_log methods."""

    def __init__(self, logger: Logger, manager: LoggerManager) -> None:
        """Initialize CustomLogger with a logger and manager."""
        self.logger = logger
        self.manager = manager

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message."""
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an info message."""
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message."""
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an error message."""
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a critical message."""
        self.logger.critical(msg, *args, **kwargs)

    def log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a message at the specified level."""
        self.logger.log(level, msg, *args, **kwargs)

    @contextmanager
    def context(self, **context_kwargs: Any) -> Iterator[CustomLogger]:
        """Delegate to LoggerManager's context method."""
        with self.manager.context(**context_kwargs):
            yield self

    async def async_log(
        self,
        level: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Delegate to LoggerManager's async_log method."""
        await self.manager.async_log(level, message, context)


class LoggerManager:
    """Logger manager with structured logging, async support, and advanced telemetry.

    Provides context-aware logging, log rotation, and enhanced metric export for
    enterprise-grade applications.
    """

    def __init__(
        self,
        name: str | LoggerConfig = "default",
        config: LoggerConfig | None = None,
    ) -> None:
        """Initialize LoggerManager with a name and configuration."""
        if isinstance(name, LoggerConfig):
            config = name
            name = config.log_file_name
        self.name = name
        self.config = config or LoggerConfig()
        self.settings = LoggerSettings(self.config)
        self._async_handlers: list[Handler] = []
        self._logger = self._configure_logger()
        self.telemetry = LoggerTelemetry(self.config, self._logger)

    def get_logger(self) -> CustomLogger:
        """Return the configured custom logger."""
        return CustomLogger(self._logger, self)

    def _configure_logger(self) -> Logger:
        """Configure a standard logger with handlers and settings."""
        logger = logging.getLogger(self.name)
        if getattr(logger, "_is_configured", False):
            return logger

        logger.setLevel(getLevelName(self.config.log_level))

        console_handler, file_handler, async_handler = self.settings.get_handlers()

        logger.addHandler(console_handler)
        if file_handler:
            logger.addHandler(file_handler)
            self._async_handlers.append(file_handler)
        if async_handler:
            logger.addHandler(async_handler)
            self._async_handlers.append(console_handler)

        logger.propagate = False
        logger._is_configured = True
        return logger

    @contextmanager
    def context(self, **context_kwargs: Any) -> Iterator[Logger]:
        """Context manager for adding contextual data to logs."""
        with contextual_log_records(**context_kwargs):
            yield self._logger

    def log_metric(
        self,
        metric_name: str,
        value: int | float,
        metric_type: MetricType = MetricType.COUNTER,
        tags: Mapping[str, str] | None = None,
    ) -> None:
        """Log a telemetry metric with support for counters, gauges, and histograms."""
        self.telemetry.record(metric_name, value, metric_type, dict(tags or {}))

    def get_metrics(self) -> dict[str, dict[str, Any]]:
        """Return collected telemetry metrics."""
        return self.telemetry.snapshot()

    def add_filter(self, name: str, filter_fn: Callable[[LogRecord], bool]) -> None:
        """Add a custom log filter."""
        if self.config.log_filters is None:
            self.config.log_filters = {}
        self.config.log_filters[name] = filter_fn
        for handler in self._logger.handlers:
            handler.addFilter(filter_fn)
        self._logger.info(f"Added log filter: {name}", extra={"filter_name": name})

    async def async_log(
        self,
        level: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Log a message asynchronously with improved error handling."""
        try:
            if not self.config.async_logging:
                self._logger.log(
                    getLevelName(level.upper()),
                    message,
                    extra={"context": context or {}},
                )
                return
            loop = asyncio.get_running_loop()

            def log_message() -> None:
                self._logger.log(
                    getLevelName(level.upper()),
                    message,
                    extra={"context": context or {}},
                )

            await loop.run_in_executor(None, log_message)
        except Exception as e:
            self._logger.error(
                f"Async logging failed: {e}",
                extra={"message": message, "error": str(e)},
            )

    def flush(self) -> None:
        """Flush all handlers to ensure logs are written."""
        for handler in self._logger.handlers:
            handler.flush()
        self._logger.debug("Log handlers flushed", extra={"stage": "flush"})
        self.settings.shutdown()

    def reset_metrics(self) -> None:
        """Reset all telemetry metrics."""
        self.telemetry.reset()

    def export_metrics_to_file(self, file_path: str | Path) -> None:
        """Export telemetry metrics to a file."""
        self.telemetry.export_to_file(file_path)
