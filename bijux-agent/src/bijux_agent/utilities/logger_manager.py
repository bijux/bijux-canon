"""Logger manager module with structured logging, async support, and telemetry.

This module provides a logger manager for enterprise-grade applications, supporting
features like context-aware logging, log rotation, and metric export.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
import datetime
from enum import Enum
import json
import logging
from logging import (
    Handler,
    Logger,
    LogRecord,
    getLevelName,
    getLogRecordFactory,
    setLogRecordFactory,
)
from logging.handlers import QueueHandler, RotatingFileHandler
from pathlib import Path
import queue
import sys
import threading
from typing import Any, ClassVar, cast

import colorlog


class MetricType(Enum):
    """Enum for supported metric types."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass
class LoggerConfig:
    """Configuration for LoggerManager with advanced settings."""

    log_dir: Path = Path("../bijux-agent_test/logs")
    log_level: str = "INFO"
    log_file_name: str = "application.log"
    max_file_size_mb: int = 10
    backup_count: int = 3
    structured_logging: bool = False
    async_logging: bool = False
    telemetry_enabled: bool = False
    log_filters: dict[str, Callable[[LogRecord], bool]] | None = None
    log_colors: dict[str, str] | None = None
    metric_export_callback: Callable[[dict[str, Any]], None] | None = None
    histogram_buckets: list[float] | None = None
    log_rotation_interval: int = 86400  # Rotate logs daily (seconds)

    DEFAULT_LOG_COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_white",
    }
    DEFAULT_HISTOGRAM_BUCKETS: ClassVar[list[float]] = [
        0.1,
        0.5,
        1.0,
        2.0,
        5.0,
        10.0,
        float("inf"),
    ]

    def __post_init__(self) -> None:
        """Initialize and validate configuration."""
        self.log_dir = Path(self.log_dir).resolve()
        self.log_level = self.log_level.upper()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_colors = self.log_colors or self.DEFAULT_LOG_COLORS
        self.histogram_buckets = (
            self.histogram_buckets or self.DEFAULT_HISTOGRAM_BUCKETS
        )


class CustomLogRecord(LogRecord):
    """Custom LogRecord to support context and metrics attributes."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize a CustomLogRecord instance."""
        super().__init__(*args, **kwargs)
        self._custom_context: dict[str, Any] = {}
        self._custom_metrics: dict[str, Any] = {}

    @property
    def custom_context(self) -> dict[str, Any]:
        """Get the custom context dictionary."""
        return self._custom_context

    @property
    def custom_metrics(self) -> dict[str, Any]:
        """Get the custom metrics dictionary."""
        return self._custom_metrics


_module_original_factory = getLogRecordFactory()


def custom_log_record_factory(*args: Any, **kwargs: Any) -> CustomLogRecord:
    """Factory for creating CustomLogRecord instances."""
    record = _module_original_factory(*args, **kwargs)
    return CustomLogRecord(
        record.name,
        record.levelno,
        record.pathname,
        record.lineno,
        record.msg,
        record.args,
        record.exc_info,
        record.funcName,
        record.stack_info,
    )


setLogRecordFactory(custom_log_record_factory)


class LoggerSettings:
    """Manages logging handlers with format and rotation settings."""

    def __init__(self, config: LoggerConfig) -> None:
        """Initialize LoggerSettings with a LoggerConfig instance."""
        self.config = config
        self._last_rotation: float = datetime.datetime.now().timestamp()
        self._rotation_lock = threading.Lock()
        self._file_handler: RotatingFileHandler | None = None
        self._async_handlers: list[Handler] = []
        self._queue_thread: threading.Thread | None = None
        self._queue: queue.Queue[LogRecord] | None = None
        self._stop_event = threading.Event()

    def get_handlers(self) -> tuple[Handler, Handler | None, Handler | None]:
        """Return console, file, and async queue handlers."""
        self._check_rotation()
        console_handler = self._get_console_handler()
        file_handler = self._get_file_handler()
        async_handler = self._get_async_handler() if self.config.async_logging else None
        self._async_handlers = []
        if file_handler:
            self._async_handlers.append(file_handler)
        if async_handler:
            self._async_handlers.append(console_handler)
        return console_handler, file_handler, async_handler

    def _check_rotation(self) -> None:
        """Rotate logs based on time interval with thread safety."""
        with self._rotation_lock:
            current_time = datetime.datetime.now().timestamp()
            if current_time - self._last_rotation >= self.config.log_rotation_interval:
                self._last_rotation = current_time
                if self._file_handler:
                    self._file_handler.doRollover()

    def _get_console_handler(self) -> Handler:
        """Create and configure a console handler."""
        handler = colorlog.StreamHandler()
        formatter = (
            colorlog.ColoredFormatter(
                "%(log_color)s%(asctime)s - [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
                log_colors=self.config.log_colors,
            )
            if not self.config.structured_logging
            else self._get_structured_formatter()
        )
        handler.setFormatter(formatter)
        if self.config.log_filters:
            for filter_fn in self.config.log_filters.values():
                handler.addFilter(filter_fn)
        return handler

    def _get_file_handler(self) -> RotatingFileHandler | None:
        """Create and configure a file handler."""
        file_path = self.config.log_dir / self.config.log_file_name
        try:
            handler = RotatingFileHandler(
                file_path,
                maxBytes=self.config.max_file_size_mb * 1024 * 1024,
                backupCount=self.config.backup_count,
            )
            formatter = (
                self._get_structured_formatter()
                if self.config.structured_logging
                else logging.Formatter(
                    "%(asctime)s - [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            handler.setFormatter(formatter)
            if self.config.log_filters:
                for filter_fn in self.config.log_filters.values():
                    handler.addFilter(filter_fn)
            self._file_handler = handler
            return handler
        except (OSError, PermissionError) as e:
            print(f"Failed to create RotatingFileHandler: {e}", file=sys.stderr)
            return None

    def _get_async_handler(self) -> QueueHandler:
        """Create and configure an async queue handler."""
        self._queue = queue.Queue[LogRecord]()
        handler = QueueHandler(self._queue)
        self._queue_thread = threading.Thread(
            target=self._process_queue,
            daemon=True,
        )
        self._queue_thread.start()
        return handler

    def _process_queue(self) -> None:
        """Process async log queue in a separate thread."""
        while not self._stop_event.is_set():
            queue_ref = self._queue
            if queue_ref is None:
                break
            try:
                record = queue_ref.get(timeout=1.0)
                if record is None:
                    break
                for handler in self._async_handlers:
                    handler.handle(record)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Async logging queue error: {e}", file=sys.stderr)

    def shutdown(self) -> None:
        """Shutdown the async logging thread cleanly."""
        self._stop_event.set()
        if self._queue:
            self._queue.put(None)
        if self._queue_thread and self._queue_thread.is_alive():
            self._queue_thread.join()

    @staticmethod
    def _get_structured_formatter() -> logging.Formatter:
        """Return a JSON formatter for structured logging with metric support."""

        class StructuredFormatter(logging.Formatter):
            def format(self, record: LogRecord) -> str:
                custom_record = cast(CustomLogRecord, record)
                log_data = {
                    "timestamp": datetime.datetime.fromtimestamp(
                        record.created
                    ).isoformat(),
                    "level": record.levelname,
                    "name": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "line": record.lineno,
                    "context": getattr(record, "context", custom_record.custom_context),
                    "metrics": getattr(record, "metrics", custom_record.custom_metrics),
                }
                return json.dumps(log_data, ensure_ascii=False)

        return StructuredFormatter()


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
        self._metric_tasks: list[asyncio.Task[Any]] = []
        self._telemetry_metrics: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "type": MetricType.COUNTER.value,
                "value": 0,
                "histogram": (
                    defaultdict(int) if self.config.histogram_buckets else None
                ),
            }
        )
        self._metrics_lock = threading.Lock()
        self._logger = self._configure_logger()

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
        current_factory = getLogRecordFactory()

        def context_log_record_factory(
            *factory_args: Any,
            **factory_kwargs: Any,
        ) -> CustomLogRecord:
            record = current_factory(*factory_args, **factory_kwargs)
            custom_record = CustomLogRecord(
                record.name,
                record.levelno,
                record.pathname,
                record.lineno,
                record.msg,
                record.args,
                record.exc_info,
                record.funcName,
                record.stack_info,
            )
            custom_record._custom_context = context_kwargs
            return custom_record

        setLogRecordFactory(context_log_record_factory)
        try:
            yield self._logger
        finally:
            setLogRecordFactory(current_factory)

    def log_metric(
        self,
        metric_name: str,
        value: int | float,
        metric_type: MetricType = MetricType.COUNTER,
        tags: Mapping[str, str] | None = None,
    ) -> None:
        """Log a telemetry metric with support for counters, gauges, and histograms."""
        if not self.config.telemetry_enabled:
            return

        tags_dict: dict[str, str] = dict(tags or {})
        with self._metrics_lock:
            metric = self._telemetry_metrics[metric_name]
            metric["type"] = metric_type.value
            metric["tags"] = tags_dict

            if metric_type == MetricType.COUNTER:
                metric["value"] += value
            elif metric_type == MetricType.GAUGE:
                metric["value"] = value
            elif metric_type == MetricType.HISTOGRAM and self.config.histogram_buckets:
                metric["value"] += value
                histogram = metric.get("histogram")
                if isinstance(histogram, dict):
                    for bucket in self.config.histogram_buckets:
                        if value <= bucket:
                            histogram[f"le_{bucket}"] = (
                                histogram.get(f"le_{bucket}", 0) + 1
                            )
                            break

            self._logger.debug(
                f"Metric recorded: {metric_name} = {value}",
                extra={
                    "metric_name": metric_name,
                    "metric_type": metric_type.value,
                    "tags": tags_dict,
                    "metrics": {
                        metric_name: {"value": value, "type": metric_type.value}
                    },
                },
            )

            if self.config.metric_export_callback:
                metric_data = {
                    "name": metric_name,
                    "type": metric_type.value,
                    "value": metric["value"],
                    "tags": tags_dict,
                    "histogram": (
                        dict(metric["histogram"])
                        if metric_type == MetricType.HISTOGRAM
                        else None
                    ),
                    "timestamp": datetime.datetime.now().isoformat(),
                }
                try:
                    task = asyncio.create_task(self._async_export_metric(metric_data))
                    self._metric_tasks.append(task)
                    self._metric_tasks = [t for t in self._metric_tasks if not t.done()]
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self._async_export_metric(metric_data))
                    loop.close()
                except Exception as e:
                    self._logger.error(
                        f"Metric export failed: {e}",
                        extra={"metric_name": metric_name, "error": str(e)},
                    )

    async def _async_export_metric(self, metric_data: dict[str, Any]) -> None:
        """Asynchronously export metric data."""
        callback = self.config.metric_export_callback
        if callback is None:
            return
        try:
            await asyncio.to_thread(callback, metric_data)
        except Exception as e:
            self._logger.error(
                f"Async metric export failed: {e}",
                extra={"metric_name": metric_data["name"], "error": str(e)},
            )

    def get_metrics(self) -> dict[str, dict[str, Any]]:
        """Return collected telemetry metrics."""
        with self._metrics_lock:
            return dict(self._telemetry_metrics)

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
        with self._metrics_lock:
            self._telemetry_metrics.clear()
        self._logger.debug("Telemetry metrics reset", extra={"stage": "metrics_reset"})

    def export_metrics_to_file(self, file_path: str | Path) -> None:
        """Export telemetry metrics to a file."""
        metrics = self.get_metrics()
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2)
            self._logger.info(
                f"Metrics exported to {file_path}",
                extra={"stage": "metrics_export"},
            )
        except Exception as e:
            self._logger.error(
                f"Metrics export to file failed: {e}",
                extra={"file_path": str(file_path), "error": str(e)},
            )
