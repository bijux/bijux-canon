"""FileReaderAgent module for Bijux Agent.

This module provides the FileReaderAgent class, which performs asynchronous
file reading, metadata extraction, and structural analysis in a multi-agent system.
It supports caching, retries, pluggable analyzers, and comprehensive audit trails,
fully integrated with LoggerManager for structured logging.
"""

from __future__ import annotations

import asyncio
from collections import Counter
from collections.abc import Callable
import hashlib
import math
from pathlib import Path
import time
from typing import Any

from bijux_agent.agents.base import BaseAgent
from bijux_agent.utilities.logger_manager import LoggerManager, MetricType

from .capabilities.universal_file_reader_core import UniversalFileReader


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

        # Preprocess context
        if self.pre_hook:
            try:
                context = self.pre_hook(context)
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
            except Exception as e:
                self.logger.error(
                    f"Pre-hook failed: {e!s}",
                    extra={"context": {"stage": "pre_hook", "error": str(e)}},
                )
                self.logger_manager.log_metric(
                    "pre_hook_errors", 1, MetricType.COUNTER, tags={"stage": "pre_hook"}
                )
                return await self.execution_kernel.error_result(
                    f"Pre-hook failed: {e!s}", context, "pre_hook"
                )

        file_path = context.get("file_path")
        if not file_path:
            self.logger.error(
                "No file_path provided",
                extra={"context": {"stage": "input_validation"}},
            )
            self.logger_manager.log_metric(
                "input_validation_errors",
                1,
                MetricType.COUNTER,
                tags={"stage": "input_validation"},
            )
            return await self.execution_kernel.error_result(
                "No 'file_path' found in context", context, "input_validation"
            )

        # Check cache
        cache_key = self._generate_cache_key(context)
        if self._cache is not None and cache_key in self._cache:
            self.logger.debug(
                "Cache hit",
                extra={"context": {"stage": "cache_check", "cache_key": cache_key}},
            )
            self.logger_manager.log_metric(
                "cache_hits", 1, MetricType.COUNTER, tags={"stage": "cache_check"}
            )
            return {**self._cache[cache_key], "cache_hit": True}

        # Determine file type and reader
        file_suffix = Path(file_path).suffix.lstrip(".").lower()
        reader = self._custom_readers.get(file_suffix, self._read_file)

        # Read file with retries
        read_result = {}
        for attempt in range(1, self.max_retries + 1):
            try:
                start = time.perf_counter()
                read_result = await reader(file_path)
                duration = time.perf_counter() - start
                read_result["read_duration_sec"] = round(duration, 4)
                read_result["attempt"] = attempt
                self.logger_manager.log_metric(
                    "file_read_duration",
                    duration,
                    MetricType.HISTOGRAM,
                    tags={
                        "stage": "file_read",
                        "attempt": str(attempt),
                        "file_type": file_suffix,
                    },
                )
                self.logger.debug(
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
                if "error" not in read_result or not read_result["error"]:
                    break
            except Exception as e:
                self.logger.error(
                    f"Read failed on attempt {attempt}: {e!s}",
                    extra={
                        "context": {
                            "stage": "file_read",
                            "attempt": attempt,
                            "error": str(e),
                            "file_type": file_suffix,
                        }
                    },
                )
                self.logger_manager.log_metric(
                    "file_read_errors",
                    1,
                    MetricType.COUNTER,
                    tags={
                        "stage": "file_read",
                        "attempt": str(attempt),
                        "file_type": file_suffix,
                    },
                )
                read_result = await self.execution_kernel.error_result(
                    str(e), context, "file_read", {"attempt": attempt}
                )
                if attempt < self.max_retries:
                    backoff_delay = self._calculate_backoff(attempt)
                    await asyncio.sleep(backoff_delay)
                    self.logger.debug(
                        "Retrying after backoff",
                        extra={
                            "context": {
                                "stage": "retry",
                                "attempt": attempt,
                                "backoff_delay": backoff_delay,
                            }
                        },
                    )

        if read_result.get("error"):
            self.logger.warning(
                "All retries failed",
                extra={"context": {"stage": "file_read", "file_path": str(file_path)}},
            )
            if self._cache is not None:
                self._cache[cache_key] = read_result
                self.logger.debug(
                    "Cached error result", extra={"context": {"cache_key": cache_key}}
                )
                self.logger_manager.log_metric(
                    "cache_stores", 1, MetricType.COUNTER, tags={"stage": "cache_store"}
                )
            return read_result

        # Apply extra analyzers
        enrichments = {}
        for analyzer in self.extra_analyzers:
            try:
                analyzer_result = analyzer(read_result)
                enrichments.update(analyzer_result)
                self.logger.debug(
                    f"Applied analyzer: {analyzer.__name__}",
                    extra={
                        "context": {
                            "stage": "analyzer",
                            "analyzer_keys": list(analyzer_result.keys()),
                        }
                    },
                )
                self.logger_manager.log_metric(
                    "analyzer_success",
                    1,
                    MetricType.COUNTER,
                    tags={"stage": "analyzer", "analyzer": analyzer.__name__},
                )
            except Exception as e:
                self.logger.warning(
                    f"Analyzer {analyzer.__name__} failed: {e!s}",
                    extra={"context": {"stage": "analyzer", "error": str(e)}},
                )
                self.logger_manager.log_metric(
                    "analyzer_errors",
                    1,
                    MetricType.COUNTER,
                    tags={"stage": "analyzer", "analyzer": analyzer.__name__},
                )
        if enrichments:
            read_result["enrichments"] = enrichments
            self.logger.debug(
                "Enrichments applied",
                extra={
                    "context": {
                        "stage": "enrichments",
                        "enrichment_keys": list(enrichments.keys()),
                    }
                },
            )

        # Auto-enrichments
        read_result.update(self._auto_enrichments(read_result))

        # Post-hook
        if self.post_hook:
            try:
                read_result = self.post_hook(context, read_result)
                self.logger.debug(
                    "Post-hook applied successfully",
                    extra={"context": {"stage": "post_hook"}},
                )
                self.logger_manager.log_metric(
                    "post_hook_success",
                    1,
                    MetricType.COUNTER,
                    tags={"stage": "post_hook"},
                )
            except Exception as e:
                self.logger.warning(
                    f"Post-hook failed: {e!s}",
                    extra={"context": {"stage": "post_hook", "error": str(e)}},
                )
                self.logger_manager.log_metric(
                    "post_hook_errors",
                    1,
                    MetricType.COUNTER,
                    tags={"stage": "post_hook"},
                )

        # Audit trail
        read_result["file_agent_audit"] = {
            "file_path": str(file_path),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "agent_version": self.version,
            "agent_id": self.id,
            "cache_enabled": self.cache_enabled,
            "async_io": self.async_io,
            "context_id": context_id,
            "file_type": file_suffix,
        }

        # Cache result
        if self._cache is not None:
            self._cache[cache_key] = read_result
            self.logger.debug(
                "Cached result", extra={"context": {"cache_key": cache_key}}
            )
            self.logger_manager.log_metric(
                "cache_stores", 1, MetricType.COUNTER, tags={"stage": "cache_store"}
            )

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
        return read_result

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
        file_path = context.get("file_path", "unknown")
        return {
            "error": msg,
            "stage": stage,
            "input": context,
            "attempt": attempt,
            "file_info": {},
            "structure_preview": {},
            "enrichments": {},
            "file_agent_audit": {
                "file_path": str(file_path),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "agent_version": str(self.version),
                "agent_id": str(self.id),
                "cache_enabled": self.cache_enabled,
                "async_io": self.async_io,
                "context_id": (str(context.get("context_id", "unknown"))),
                "file_type": Path(file_path).suffix.lstrip(".").lower(),
            },
            "cache_hit": False,
            "action_plan": [f"Fix file read error: {msg}"],
        }

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate backoff delay based on the strategy.

        Args:
            attempt: Current attempt number.

        Returns:
            Delay in seconds.
        """
        if self.backoff_strategy == "exponential":
            return 0.5 * (2 ** (attempt - 1))  # Exponential: 0.5s, 1s, 2s, ...
        else:  # Linear
            return 0.5 * attempt  # Linear: 0.5s, 1s, 1.5s, ...

    def _auto_enrichments(self, result: dict[str, Any]) -> dict[str, Any]:
        """Generate automatic enrichments with advanced telemetry.

        Args:
            result: The file read result to enrich.

        Returns:
            Dictionary of enrichments.
        """
        enrich = {}
        text = result.get("text", "")
        file_info = result.get("file_info", {})
        structure = result.get("structure_preview", {})
        file_path = file_info.get("file_path", "unknown") if file_info else "unknown"
        file_type = Path(file_path).suffix.lstrip(".").lower()
        tags = {
            "stage": "auto_enrichments",
            "agent": "FileReaderAgent",
            "file_type": file_type,
        }

        # Text-based enrichments
        if isinstance(text, str) and text:
            try:
                text_head = text[:400]
                text_tail = text[-200:] if len(text) > 600 else ""
                n_chars = len(text)
                n_lines = text.count("\n") + 1
                n_words = len(text.split())
                avg_word_length = sum(len(word) for word in text.split()) / max(
                    n_words, 1
                )
                entropy = self._text_entropy(text)
                text_complexity = self._text_complexity(text)

                enrich["text_head"] = text_head
                enrich["text_tail"] = text_tail
                enrich["n_chars"] = n_chars
                enrich["n_lines"] = n_lines
                enrich["n_words"] = n_words
                enrich["avg_word_length"] = avg_word_length
                enrich["entropy"] = entropy
                enrich["text_complexity"] = text_complexity

                # Log metrics with tags
                self.logger_manager.log_metric(
                    "text_length_chars", enrich["n_chars"], MetricType.GAUGE, tags=tags
                )
                self.logger_manager.log_metric(
                    "text_lines", enrich["n_lines"], MetricType.GAUGE, tags=tags
                )
                self.logger_manager.log_metric(
                    "text_words", enrich["n_words"], MetricType.GAUGE, tags=tags
                )
                self.logger_manager.log_metric(
                    "avg_word_length",
                    enrich["avg_word_length"],
                    MetricType.HISTOGRAM,
                    tags=tags,
                )
                self.logger_manager.log_metric(
                    "text_entropy", enrich["entropy"], MetricType.HISTOGRAM, tags=tags
                )
                self.logger_manager.log_metric(
                    "text_complexity",
                    enrich["text_complexity"],
                    MetricType.HISTOGRAM,
                    tags=tags,
                )

                self.logger.debug(
                    "Text enrichments computed",
                    extra={
                        "context": {
                            "stage": "auto_enrichments",
                            "metrics": {
                                "n_chars": enrich["n_chars"],
                                "n_lines": enrich["n_lines"],
                                "n_words": enrich["n_words"],
                                "avg_word_length": enrich["avg_word_length"],
                                "entropy": enrich["entropy"],
                                "text_complexity": enrich["text_complexity"],
                            },
                            "tags": tags,
                        }
                    },
                )
            except Exception as e:
                self.logger.error(
                    f"Text enrichment failed: {e!s}",
                    extra={
                        "context": {
                            "stage": "auto_enrichments",
                            "error": str(e),
                            "tags": tags,
                        }
                    },
                )
                self.logger_manager.log_metric(
                    "text_enrichment_errors", 1, MetricType.COUNTER, tags=tags
                )

        # File metadata enrichments
        if file_info:
            try:
                file_size_bytes = file_info.get("file_size_bytes", 0)
                file_size_kb = round(file_size_bytes / 1024, 2)
                file_size_mb = round(file_size_kb / 1024, 2)
                enrich["file_size_kb"] = file_size_kb
                enrich["file_size_mb"] = file_size_mb
                enrich["file_type"] = file_info.get("file_type", file_type)
                enrich["last_modified"] = str(file_info.get("last_modified", ""))

                file_tags = {"file_type": enrich["file_type"], **tags}
                self.logger_manager.log_metric(
                    "file_size_mb",
                    enrich["file_size_mb"],
                    MetricType.GAUGE,
                    tags=file_tags,
                )
                self.logger.debug(
                    "File metadata enrichments computed",
                    extra={
                        "context": {
                            "stage": "auto_enrichments",
                            "metrics": {
                                "file_size_mb": enrich["file_size_mb"],
                                "file_type": enrich["file_type"],
                            },
                            "tags": file_tags,
                        }
                    },
                )
            except Exception as e:
                self.logger.error(
                    f"File metadata enrichment failed: {e!s}",
                    extra={
                        "context": {
                            "stage": "auto_enrichments",
                            "error": str(e),
                            "tags": tags,
                        }
                    },
                )
                self.logger_manager.log_metric(
                    "file_metadata_errors", 1, MetricType.COUNTER, tags=tags
                )

        # Structural preview
        if structure:
            try:
                structure_sections = structure.get("sections", [])
                structure_tables = structure.get("tables", [])
                structure_images = structure.get("images", [])
                section_depths = [
                    section.get("depth", 1) for section in structure_sections
                ]
                max_section_depth = max(section_depths, default=1)
                enrich["structure_summary"] = {
                    "n_sections": len(structure_sections),
                    "has_tables": bool(structure_tables),
                    "has_images": bool(structure_images),
                    "max_section_depth": max_section_depth,
                }
                self.logger_manager.log_metric(
                    "n_sections",
                    enrich["structure_summary"]["n_sections"],
                    MetricType.GAUGE,
                    tags=tags,
                )
                self.logger_manager.log_metric(
                    "max_section_depth",
                    enrich["structure_summary"]["max_section_depth"],
                    MetricType.GAUGE,
                    tags=tags,
                )
                self.logger.debug(
                    "Structure summary computed",
                    extra={
                        "context": {
                            "stage": "auto_enrichments",
                            "structure_summary": enrich["structure_summary"],
                            "tags": tags,
                        }
                    },
                )
            except Exception as e:
                self.logger.error(
                    f"Structure enrichment failed: {e!s}",
                    extra={
                        "context": {
                            "stage": "auto_enrichments",
                            "error": str(e),
                            "tags": tags,
                        }
                    },
                )
                self.logger_manager.log_metric(
                    "structure_enrichment_errors", 1, MetricType.COUNTER, tags=tags
                )

        return enrich

    @staticmethod
    def _text_entropy(text: str) -> float:
        """Calculate Shannon entropy of text.

        Args:
            text: Input text to analyze.

        Returns:
            Entropy value.
        """
        if not text:
            return 0.0
        counts = Counter(text)
        total = len(text)
        return round(
            -sum((n / total) * math.log2(n / total) for n in counts.values()), 4
        )

    @staticmethod
    def _text_complexity(text: str) -> float:
        """Estimate text complexity based on word length and uniqueness.

        Args:
            text: Input text to analyze.

        Returns:
            Complexity score.
        """
        if not text:
            return 0.0
        words = [w for w in text.split() if w.strip()]
        if not words:
            return 0.0
        avg_word_length = sum(len(w) for w in words) / len(words)
        unique_words = len(set(words))
        return round(avg_word_length * (unique_words / len(words)), 2)

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
        self.logger.debug(
            "Generated cache key",
            extra={
                "context": {"stage": "cache_key_generation", "cache_key": cache_key}
            },
        )
        self.logger_manager.log_metric(
            "cache_key_generated",
            1,
            MetricType.COUNTER,
            tags={"stage": "cache_key_generation"},
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
        return {
            "file_path": "str (required)",
            "text": "str (if applicable)",
            "warnings": "list[str]",
            "error": "str (if error occurred)",
            "file_info": {
                "file_size_bytes": "int",
                "file_type": "str",
                "last_modified": "str",
            },
            "structure_preview": {
                "sections": "list",
                "tables": "list",
                "images": "list",
            },
            "enrichments": {
                "text_head": "str",
                "text_tail": "str",
                "n_chars": "int",
                "n_lines": "int",
                "n_words": "int",
                "avg_word_length": "float",
                "entropy": "float",
                "text_complexity": "float",
                "file_size_kb": "float",
                "file_size_mb": "float",
                "file_type": "str",
                "last_modified": "str",
                "structure_summary": {
                    "n_sections": "int",
                    "has_tables": "bool",
                    "has_images": "bool",
                    "max_section_depth": "int",
                },
            },
            "file_agent_audit": {
                "file_path": "str",
                "timestamp": "str",
                "agent_version": "str",
                "agent_id": "str",
                "cache_enabled": "bool",
                "async_io": "bool",
                "context_id": "str",
                "file_type": "str",
            },
            "read_duration_sec": "float",
            "attempt": "int",
            "cache_hit": "bool",
            "action_plan": "list[str]",
        }

    @classmethod
    def coverage_report(cls, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Describe the parts of the context this agent consumes or modifies."""
        consumes = ["file_path"]
        produces = [
            "text",
            "page_count",
            "ocr_used",
            "warnings",
            "file_info",
            "processing_profile",
            "structure_preview",
            "audit_trail",
            "read_duration_sec",
            "attempt",
            "text_head",
            "text_tail",
            "n_chars",
            "n_lines",
            "n_words",
            "avg_word_length",
            "entropy",
            "text_complexity",
            "file_size_kb",
            "file_size_mb",
            "file_type",
            "last_modified",
            "structure_summary",
            "file_agent_audit",
        ]
        return {"consumes": consumes, "modifies": [], "produces": produces}

    def flush_logs(self) -> None:
        """Flush all log handlers."""
        try:
            # LoggerManager.flush() is synchronous and returns None
            self.logger_manager.flush()
            self.logger.debug("Logs flushed", extra={"context": {"stage": "log_flush"}})
            self.logger_manager.log_metric(
                "log_flush", 1, MetricType.COUNTER, tags={"stage": "log_flush"}
            )
        except Exception as e:
            self.logger.error(
                f"Failed to flush logs: {e!s}",
                extra={"context": {"stage": "log_flush", "error": str(e)}},
            )

    async def get_telemetry(self) -> dict[str, dict[str, Any]]:
        """Retrieve telemetry metrics."""
        try:
            # LoggerManager.get_metrics() is synchronous and returns a dict
            metrics = self.logger_manager.get_metrics()
            self.logger.debug(
                "Telemetry metrics retrieved",
                extra={
                    "context": {
                        "stage": "telemetry",
                        "metric_names": list(metrics.keys()),
                    }
                },
            )
            self.logger_manager.log_metric(
                "telemetry_retrieved",
                1,
                MetricType.COUNTER,
                tags={"stage": "telemetry"},
            )
            return metrics
        except Exception as e:
            self.logger.error(
                f"Failed to retrieve telemetry: {e!s}",
                extra={"context": {"stage": "telemetry", "error": str(e)}},
            )
            return {}

    def reset_telemetry(self) -> None:
        """Reset telemetry metrics."""
        try:
            # LoggerManager.reset_metrics() is synchronous and returns None
            self.logger_manager.reset_metrics()
            self.logger.debug(
                "Telemetry metrics reset",
                extra={"context": {"stage": "reset_telemetry"}},
            )
            self.logger_manager.log_metric(
                "metrics_reset",
                1,
                MetricType.COUNTER,
                tags={"stage": "reset_telemetry"},
            )
        except Exception as e:
            self.logger.error(
                f"Failed to reset telemetry: {e!s}",
                extra={"context": {"stage": "reset_telemetry", "error": str(e)}},
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
