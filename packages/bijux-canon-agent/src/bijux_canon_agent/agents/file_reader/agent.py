"""FileReaderAgent module for Bijux Agent.

This module provides the FileReaderAgent class, which performs asynchronous
file reading, metadata extraction, and structural analysis in a multi-agent system.
It supports caching, retries, pluggable analyzers, and comprehensive audit trails,
fully integrated with LoggerManager for structured logging.
"""

from __future__ import annotations

from collections.abc import Callable
import hashlib
from typing import Any

from bijux_canon_agent.agents.base import BaseAgent
from bijux_canon_agent.observability.logging import LoggerManager, MetricType

from .capabilities.universal_file_reader_core import UniversalFileReader
from .reporting import (
    build_coverage_report,
    build_file_reader_error_payload,
    build_self_report_schema,
)
from .read_request import build_file_read_request
from .result_assembly import (
    apply_extra_analyzers,
    finalize_read_result,
)
from .runtime_flow import (
    load_cached_result,
    read_with_retries,
    store_cached_result,
)
from .telemetry_support import (
    emit_cache_key_metric,
    flush_agent_logs,
    get_agent_telemetry,
    reset_agent_telemetry,
)


class FileReaderAgent(BaseAgent):
    """Enhanced FileReaderAgent for a multi-agent system.

    Performs async file reading, metadata extraction, and structural analysis.
    Supports caching, retries, pluggable analyzers, and comprehensive audit trails.
    Fully integrated with LoggerManager for structured, async, and telemetry-enabled
    logging.
    """

    def __init__(
        self,
        config: dict[str, Any],
        logger_manager: LoggerManager,
        pre_hook: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        post_hook: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
        | None = None,
        extra_analyzers: list[Callable[[dict[str, Any]], dict[str, Any]]] | None = None,
    ):
        """Initialize the FileReaderAgent with configuration and logger manager.

        Args:
            config: Configuration settings (e.g., file types, retry policies).
            logger_manager: The LoggerManager instance for logging.
            pre_hook: Optional function called before reading (e.g., transform
                      context).
            post_hook: Optional function called after reading (e.g., enrich
                       results).
            extra_analyzers: List of analyzer functions to enrich the result.
        """
        super().__init__(config, logger_manager)
        self.ufa = UniversalFileReader(config.get("file_reader", {}))
        self.pre_hook = pre_hook
        self.post_hook = post_hook
        self.extra_analyzers = extra_analyzers or []

        # Load configuration settings
        self.max_retries = self.config.get("max_retries", 3)
        self.cache_enabled = self.config.get("cache_enabled", True)
        self.async_io = self.config.get("async_io", True)
        self.backoff_strategy = self.config.get("backoff_strategy", "exponential")
        self._version = self.config.get("agent_version", "2.0.0")
        self._agent_id = self.config.get(
            "agent_id",
            str(hashlib.sha256(self.__class__.__name__.encode()).hexdigest()),
        )

        # Validate backoff strategy
        if self.backoff_strategy not in ["exponential", "linear"]:
            raise ValueError(f"Unsupported backoff strategy: {self.backoff_strategy}")

        # Cache for file read results
        self._cache: dict[str, dict[str, Any]] | None = (
            {} if self.cache_enabled else None
        )
        self._custom_readers: dict[str, Callable[[str], dict[str, Any]]] = {}

        self.logger.info(
            "FileReaderAgent initialized",
            extra={
                "context": {
                    "agent_id": self._agent_id,
                    "version": self._version,
                    "config": {
                        "cache_enabled": self.cache_enabled,
                        "async_io": self.async_io,
                        "max_retries": self.max_retries,
                        "backoff_strategy": self.backoff_strategy,
                    },
                }
            },
        )

    def _initialize(self) -> None:
        """Initialize the agent by setting up any necessary resources.

        Currently, no additional initialization is required beyond what's done in
        __init__.
        """
        pass

    def _cleanup(self) -> None:
        """Clean up resources used by the agent.

        Currently, no additional cleanup is required.
        """
        pass

    @property
    def capabilities(self) -> list[str]:
        """List of capabilities this agent supports."""
        return ["file_reading"]

    @property
    def version(self) -> str:
        """Return the agent version."""
        return self._version

    @property
    def id(self) -> str:
        """Return the agent ID."""
        return self._agent_id

    async def _run_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run the file reader with async I/O, caching, and retries.

        Processes the file, applies analyzers, and generates enrichments.

        Args:
            context: Input context containing the file path under 'file_path'.

        Returns:
            Dictionary with extracted text, metadata, and other details.
        """
        context_id = context.get(
            "context_id", str(hashlib.sha256(str(context).encode()).hexdigest())
        )
        with self.logger.context(agent="FileReaderAgent", context_id=context_id):
            self.logger.info(
                "Starting file read operation",
                extra={
                    "context": {
                        "file_path": context.get("file_path", "unknown"),
                        "stage": "init",
                    }
                },
            )
            context, pre_hook_error = self._apply_pre_hook(context)
            if pre_hook_error is not None:
                return await self.execution_kernel.error_result(
                    pre_hook_error,
                    context,
                    "pre_hook",
                )
            cache_key = self._generate_cache_key(context)
            request = build_file_read_request(
                context=context,
                cache_key=cache_key,
                logger=self.logger,
                logger_manager=self.logger_manager,
            )
            if request is None:
                return await self.execution_kernel.error_result(
                    "No 'file_path' found in context",
                    context,
                    "input_validation",
                )

            cached_result = load_cached_result(
                self._cache,
                request.cache_key,
                logger=self.logger,
                logger_manager=self.logger_manager,
            )
            if cached_result is not None:
                return cached_result

            read_result = await read_with_retries(
                context=context,
                file_path=request.file_path,
                file_suffix=request.file_suffix,
                custom_readers=self._custom_readers,
                default_reader=self._read_file,
                max_retries=self.max_retries,
                backoff_strategy=self.backoff_strategy,
                logger=self.logger,
                logger_manager=self.logger_manager,
                error_result=self.execution_kernel.error_result,
            )
            if read_result.get("error"):
                self.logger.warning(
                    "All retries failed",
                    extra={
                        "context": {
                            "stage": "file_read",
                            "file_path": request.file_path,
                        }
                    },
                )
                store_cached_result(
                    self._cache,
                    request.cache_key,
                    read_result,
                    logger=self.logger,
                    logger_manager=self.logger_manager,
                )
                return read_result

            apply_extra_analyzers(
                read_result,
                self.extra_analyzers,
                logger=self.logger,
                logger_manager=self.logger_manager,
            )
            read_result = finalize_read_result(
                read_result,
                context=context,
                post_hook=self.post_hook,
                file_path=request.file_path,
                context_id=context_id,
                file_suffix=request.file_suffix,
                agent_version=str(self.version),
                agent_id=str(self.id),
                cache_enabled=self.cache_enabled,
                async_io=self.async_io,
                logger=self.logger,
                logger_manager=self.logger_manager,
            )
            store_cached_result(
                self._cache,
                request.cache_key,
                read_result,
                logger=self.logger,
                logger_manager=self.logger_manager,
            )
            await self._log_completion(
                request.file_path,
                request.file_suffix,
                read_result,
            )
            return read_result

    def _apply_pre_hook(
        self, context: dict[str, Any]
    ) -> tuple[dict[str, Any], str | None]:
        """Apply the optional pre-hook to the run context."""
        if not self.pre_hook:
            return context, None
        try:
            updated_context = self.pre_hook(context)
            self.logger.debug(
                "Pre-hook applied successfully",
                extra={"context": {"stage": "pre_hook"}},
            )
            self.logger_manager.log_metric(
                "pre_hook_success",
                1,
                MetricType.COUNTER,
                tags={"stage": "pre_hook"},
            )
            return updated_context, None
        except Exception as exc:
            self.logger.error(
                f"Pre-hook failed: {exc!s}",
                extra={"context": {"stage": "pre_hook", "error": str(exc)}},
            )
            self.logger_manager.log_metric(
                "pre_hook_errors",
                1,
                MetricType.COUNTER,
                tags={"stage": "pre_hook"},
            )
            return context, f"Pre-hook failed: {exc!s}"

    async def _log_completion(
        self,
        file_path: str,
        file_suffix: str,
        read_result: dict[str, Any],
    ) -> None:
        """Log successful file-read completion to both sync and async sinks."""
        self.logger.info(
            "File read completed successfully",
            extra={
                "context": {
                    "stage": "completion",
                    "file_path": str(file_path),
                    "output_keys": list(read_result.keys()),
                    "file_type": file_suffix,
                }
            },
        )
        await self.logger.async_log(
            "INFO",
            "File read operation completed",
            {
                "file_path": str(file_path),
                "duration": read_result.get("read_duration_sec", 0),
                "attempt": read_result.get("attempt", 1),
                "file_type": file_suffix,
            },
        )

    async def _read_file(self, file_path: str) -> dict[str, Any]:
        """Read file asynchronously using UniversalFileReader.

        Args:
            file_path: Path to the file to read.

        Returns:
            Dictionary containing the file content and metadata.
        """
        self.logger.debug(
            "Initiating async file read",
            extra={"context": {"stage": "async_read", "file_path": str(file_path)}},
        )
        result = await self.ufa.read_file(file_path)
        self.logger.debug(
            "Async file read completed",
            extra={
                "context": {
                    "stage": "async_read",
                    "file_path": str(file_path),
                    "result_keys": list(result.keys()),
                }
            },
        )
        return result

    def error_payload(
        self,
        msg: str,
        context: dict[str, Any],
        stage: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a standardized error result with async logging."""
        attempt = 1
        if extra and "attempt" in extra:
            attempt = int(extra["attempt"])
        return build_file_reader_error_payload(
            msg,
            context,
            stage,
            attempt=attempt,
            agent_version=str(self.version),
            agent_id=str(self.id),
            cache_enabled=self.cache_enabled,
            async_io=self.async_io,
        )

    def _generate_cache_key(self, context: dict[str, Any]) -> str:
        """Generate a cache key based on context.

        Args:
            context: Input context.

        Returns:
            Cache key string.
        """
        context_str = str(
            sorted(
                {
                    k: v for k, v in context.items() if k not in ["timestamp", "nonce"]
                }.items()
            )
        )
        cache_key = str(hashlib.sha256(context_str.encode()).hexdigest())
        emit_cache_key_metric(
            cache_key,
            logger=self.logger,
            logger_manager=self.logger_manager,
        )
        return cache_key

    def register_analyzer(
        self, analyzer: Callable[[dict[str, Any]], dict[str, Any]]
    ) -> None:
        """Dynamically register a new analyzer.

        Args:
            analyzer: Function to analyze and enrich the file read result.
        """
        self.extra_analyzers.append(analyzer)
        self.logger.info(
            f"Registered analyzer: {analyzer.__name__}",
            extra={
                "context": {
                    "stage": "analyzer_registration",
                    "analyzer": analyzer.__name__,
                }
            },
        )
        self.logger_manager.log_metric(
            "analyzers_registered",
            1,
            MetricType.COUNTER,
            tags={"analyzer": analyzer.__name__},
        )

    def register_custom_reader(
        self, file_extension: str, reader: Callable[[str], dict[str, Any]]
    ) -> None:
        """Register a custom file reader for a specific file extension.

        Args:
            file_extension: File extension (e.g., "pdf").
            reader: Function to read the file.
        """
        file_extension = file_extension.lstrip(".").lower()
        self._custom_readers[file_extension] = reader
        self.logger.info(
            f"Registered custom reader for extension: {file_extension}",
            extra={
                "context": {"stage": "reader_registration", "extension": file_extension}
            },
        )
        self.logger_manager.log_metric(
            "custom_readers_registered",
            1,
            MetricType.COUNTER,
            tags={"extension": file_extension},
        )

    @classmethod
    def self_report_schema(cls) -> dict[str, Any]:
        """Return the output schema for documentation and validation."""
        return build_self_report_schema()

    @classmethod
    def coverage_report(cls, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Describe the parts of the context this agent consumes or modifies."""
        return build_coverage_report()

    def flush_logs(self) -> None:
        """Flush all log handlers."""
        flush_agent_logs(logger=self.logger, logger_manager=self.logger_manager)

    async def get_telemetry(self) -> dict[str, dict[str, Any]]:
        """Retrieve telemetry metrics."""
        return await get_agent_telemetry(
            logger=self.logger,
            logger_manager=self.logger_manager,
        )

    def reset_telemetry(self) -> None:
        """Reset telemetry metrics."""
        reset_agent_telemetry(
            logger=self.logger,
            logger_manager=self.logger_manager,
        )

    async def shutdown(self) -> None:
        """Shutdown the agent and flush logs."""
        self.logger.info(
            "Shutting down FileReaderAgent", extra={"context": {"stage": "shutdown"}}
        )
        self.flush_logs()
        self.logger.info(
            "FileReaderAgent shutdown complete",
            extra={"context": {"stage": "shutdown"}},
        )
        await super().shutdown()
