"""Handler and record-factory support for agent logging."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
import datetime
import json
import logging
from logging import (
    Handler,
    LogRecord,
    getLogRecordFactory,
    setLogRecordFactory,
)
from logging.handlers import QueueHandler, RotatingFileHandler
from pathlib import Path
import queue
import sys
import threading
from typing import Any, ClassVar, Iterator, cast

import colorlog


@dataclass
class LoggerConfig:
    """Configuration for LoggerManager with advanced settings."""

    log_dir: Path = Path("../bijux-canon-agent_test/logs")
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
    log_rotation_interval: int = 86400

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
        super().__init__(*args, **kwargs)
        self._custom_context: dict[str, Any] = {}
        self._custom_metrics: dict[str, Any] = {}

    @property
    def custom_context(self) -> dict[str, Any]:
        return self._custom_context

    @property
    def custom_metrics(self) -> dict[str, Any]:
        return self._custom_metrics


def install_custom_log_record_factory() -> None:
    """Install the shared custom log record factory once per process."""
    original_factory = getLogRecordFactory()

    def custom_log_record_factory(*args: Any, **kwargs: Any) -> CustomLogRecord:
        record = original_factory(*args, **kwargs)
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


@contextmanager
def contextual_log_records(**context_kwargs: Any) -> Iterator[None]:
    """Temporarily attach structured context to new log records."""
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
        yield
    finally:
        setLogRecordFactory(current_factory)


class LoggerSettings:
    """Manage logging handlers with format and rotation settings."""

    def __init__(self, config: LoggerConfig) -> None:
        self.config = config
        self._last_rotation: float = datetime.datetime.now().timestamp()
        self._rotation_lock = threading.Lock()
        self._file_handler: RotatingFileHandler | None = None
        self._async_handlers: list[Handler] = []
        self._queue_thread: threading.Thread | None = None
        self._queue: queue.Queue[LogRecord] | None = None
        self._stop_event = threading.Event()

    def get_handlers(self) -> tuple[Handler, Handler | None, Handler | None]:
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
        with self._rotation_lock:
            current_time = datetime.datetime.now().timestamp()
            if current_time - self._last_rotation >= self.config.log_rotation_interval:
                self._last_rotation = current_time
                if self._file_handler:
                    self._file_handler.doRollover()

    def _get_console_handler(self) -> Handler:
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
        except (OSError, PermissionError) as exc:
            print(f"Failed to create RotatingFileHandler: {exc}", file=sys.stderr)
            return None

    def _get_async_handler(self) -> QueueHandler:
        self._queue = queue.Queue[LogRecord]()
        handler = QueueHandler(self._queue)
        self._queue_thread = threading.Thread(
            target=self._process_queue,
            daemon=True,
        )
        self._queue_thread.start()
        return handler

    def _process_queue(self) -> None:
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
            except Exception as exc:
                print(f"Async logging queue error: {exc}", file=sys.stderr)

    def shutdown(self) -> None:
        self._stop_event.set()
        if self._queue:
            self._queue.put(None)
        if self._queue_thread and self._queue_thread.is_alive():
            self._queue_thread.join()

    @staticmethod
    def _get_structured_formatter() -> logging.Formatter:
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


__all__ = [
    "CustomLogRecord",
    "LoggerConfig",
    "LoggerSettings",
    "contextual_log_records",
    "install_custom_log_record_factory",
]
