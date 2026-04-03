"""SummarizerAgent module for Bijux Agent.

This module provides the SummarizerAgent class for enhanced text summarization
in a multi-agent system. It supports chunking, multiple strategies (extractive,
abstractive, hybrid), section-aware summarization, iterative revision, and
structured summaries.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
import hashlib
import re
import time
from typing import Any, TypedDict, cast

from bijux_agent.agents.base import BaseAgent
from bijux_agent.utilities.llm_utils import LLMUtils
from bijux_agent.utilities.logger_manager import LoggerManager, MetricType

from .rules import (
    abstractive,
    extractive,
    postprocessing,
)


class SummarizerSummary(TypedDict):
    """Structured summary payload."""

    executive_summary: str
    key_points: list[str]
    actionable_insights: str
    critical_risks: str
    missing_info: str


class SummarizerAudit(TypedDict):
    """Audit metadata for summarization runs."""

    timestamp: str
    duration_sec: float
    input_tokens: int
    output_tokens: int
    chunks_processed: int


class SummarizerResult(TypedDict):
    """TypedDict for a successful summarization result."""

    summary: SummarizerSummary
    method: str
    input_length: int
    backend: str
    strategy: str
    warnings: list[str]
    audit: SummarizerAudit


class SummarizerErrorResult(SummarizerResult, total=False):
    """TypedDict describing an error result."""

    error: str
    stage: str
    input: dict[str, Any]


class SummarizerAgent(BaseAgent):
    """Enhanced summarization agent for a multi-agent system.

    Supports chunking, section-aware summarization, multiple strategies (extractive,
    abstractive, hybrid), iterative revision based on feedback, and audit trails.
    Produces structured summaries with executive summary, key points, actionable
    insights, critical risks, and missing information.
    """

    # Supported summarization strategies
    STRATEGY_EXTRACTIVE = "extractive"
    STRATEGY_ABSTRACTIVE = "abstractive"
    STRATEGY_HYBRID = "hybrid"

    def __init__(
        self,
        config: dict[str, Any],
        logger_manager: LoggerManager,
        pre_hook: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        post_hook: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
        | None = None,
    ):
        """Initialize SummarizerAgent with config and logger manager.

        Args:
            config: Dict with settings like max_length, strategy, etc.
            logger_manager: LoggerManager instance for logging.
            pre_hook: Optional function called before summarization.
            post_hook: Optional function called after summarization.
        """
        super().__init__(config, logger_manager)
        self.pre_hook = pre_hook
        self.post_hook = post_hook

        # Load configuration settings
        self.max_length = self.config.get("max_length", 2048)
        self.max_tokens = self.config.get("max_tokens", 512)
        self.backend = self.config.get("backend", "simple")
        self.chunk_size = self.config.get("chunk_size", 1024)
        self.strategy = self.config.get("strategy", self.STRATEGY_HYBRID)
        self.strategy_weights = self.config.get(
            "strategy_weights",
            {self.STRATEGY_EXTRACTIVE: 0.6, self.STRATEGY_ABSTRACTIVE: 0.4},
        )
        self._cache: dict[str, SummarizerResult] | None = (
            {} if self.config.get("enable_cache", True) else None
        )
        self.max_retries = self.config.get("max_retries", 2)
        self.min_keyword_length = self.config.get("min_keyword_length", 3)
        self.top_keywords_count = self.config.get("top_keywords_count", 10)

        # Validate strategy and weights
        if self.strategy not in [
            self.STRATEGY_EXTRACTIVE,
            self.STRATEGY_ABSTRACTIVE,
            self.STRATEGY_HYBRID,
        ]:
            raise ValueError(f"Unsupported strategy: {self.strategy}")
        if self.strategy == self.STRATEGY_HYBRID:
            total_weight = sum(self.strategy_weights.values())
            if abs(total_weight - 1.0) > 0.01:
                raise ValueError(
                    f"Strategy weights must sum to 1 for hybrid strategy, "
                    f"got {total_weight}"
                )

        # Initialize LLM if needed
        self.llm = None
        if self.backend != "simple" and self.strategy in [
            self.STRATEGY_ABSTRACTIVE,
            self.STRATEGY_HYBRID,
        ]:
            self.llm = LLMUtils(self.config)

        self.logger.info(
            "SummarizerAgent initialized",
            extra={
                "context": {
                    "config": {
                        "max_length": self.max_length,
                        "max_tokens": self.max_tokens,
                        "backend": self.backend,
                        "chunk_size": self.chunk_size,
                        "strategy": self.strategy,
                        "strategy_weights": self.strategy_weights,
                        "enable_cache": bool(self._cache),
                        "has_llm": self.llm is not None,
                        "max_retries": self.max_retries,
                        "min_keyword_length": self.min_keyword_length,
                        "top_keywords_count": self.top_keywords_count,
                    }
                }
            },
        )

    def _initialize(self) -> None:
        """Initialize the agent by setting up any necessary resources."""
        pass

    def _cleanup(self) -> None:
        """Clean up resources used by the agent."""
        if self._cache is not None:
            self._cache.clear()
            self.logger.debug(
                "Cache cleared during cleanup",
                extra={"context": {"stage": "cleanup"}},
            )

    @property
    def capabilities(self) -> list[str]:
        """List of capabilities this agent supports."""
        return ["summarization"]

    async def _run_payload(
        self, context: dict[str, Any]
    ) -> SummarizerResult | SummarizerErrorResult:
        """Run the summarizer with chunking, section awareness, and error handling.

        Produces a structured summary in the format:
        - Executive Summary (1-2 sentences)
        - Key Points (bulleted)
        - Actionable Insights
        - Critical Risks/Caveats
        - Missing/Unclear Info

        Args:
            context: Input context with text to summarize under 'text' or nested.

        Returns:
            Dict with structured summary and metadata.
        """
        context_id = context.get(
            "context_id", str(hashlib.sha256(str(context).encode()).hexdigest())
        )
        with self.logger.context(agent="SummarizerAgent", context_id=context_id):
            self.logger.info(
                "Starting summarization operation",
                extra={"context": {"stage": "init", "context_id": context_id}},
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
                        "pre_hook_errors",
                        1,
                        MetricType.COUNTER,
                        tags={"stage": "pre_hook"},
                    )
                    return cast(
                        SummarizerErrorResult,
                        await self.execution_kernel.error_result(
                            f"Pre-hook failed: {e!s}", context, "pre_hook"
                        ),
                    )

            # Extract text and task goal
            text = self._extract_text(context)
            if not text:
                self.logger.error(
                    "No valid text provided for summarization",
                    extra={"context": {"stage": "input_validation"}},
                )
                self.logger_manager.log_metric(
                    "input_validation_errors",
                    1,
                    MetricType.COUNTER,
                    tags={"stage": "input_validation"},
                )
                return cast(
                    SummarizerErrorResult,
                    await self.execution_kernel.error_result(
                        "No valid text provided in context",
                        context,
                        "input_validation",
                    ),
                )

            task_goal = context.get("task_goal", "summarize the text")
            keywords = self._extract_keywords(text, task_goal)

            # Check cache
            cache_key = hashlib.sha256((text + task_goal).encode()).hexdigest()
            if self._cache is not None and cache_key in self._cache:
                self.logger.debug(
                    "Returning cached summarization result",
                    extra={"context": {"cache_key": cache_key}},
                )
                self.logger_manager.log_metric(
                    "cache_hits", 1, MetricType.COUNTER, tags={"stage": "cache_check"}
                )
                return cast(SummarizerResult, self._cache[cache_key])

            # Handle feedback for revision
            retry_instruction = context.get("feedback", "")
            prompt_prefix = ""
            if retry_instruction:
                prompt_prefix = (
                    f"Previous summary had issues. {retry_instruction}. "
                    f"Please revise accordingly:\n\n"
                )
                self.logger.info(
                    "Applying revision instruction",
                    extra={
                        "context": {
                            "stage": "revision",
                            "retry_instruction": retry_instruction,
                        }
                    },
                )

            # Summarize with retry mechanism
            start_time = time.perf_counter()
            summary_text, method = None, None
            for attempt in range(self.max_retries + 1):
                try:
                    summary_text, method = await self._summarize(
                        text, prompt_prefix, task_goal, keywords
                    )
                    break
                except Exception as e:
                    error_msg = (
                        f"Summarization attempt {attempt + 1}/"
                        f"{self.max_retries + 1} failed: {e!s}"
                    )
                    self.logger.error(
                        error_msg,
                        extra={"context": {"stage": "summarization", "error": str(e)}},
                    )
                    if attempt == self.max_retries:
                        self.logger_manager.log_metric(
                            "summarization_errors",
                            1,
                            MetricType.COUNTER,
                            tags={"stage": "summarization"},
                        )
                        error_msg = (
                            f"Summarization failed after {self.max_retries + 1} "
                            f"attempts: {e!s}"
                        )
                        return cast(
                            SummarizerErrorResult,
                            await self.execution_kernel.error_result(
                                error_msg,
                                context,
                                "summarization",
                            ),
                        )

            summary_text = summary_text or ""
            method = method or ""
            duration = time.perf_counter() - start_time
            self.logger_manager.log_metric(
                "summarization_duration",
                duration,
                MetricType.HISTOGRAM,
                tags={"stage": "summarization"},
            )

            # Structure the summary
            structured_summary = cast(
                SummarizerSummary,
                postprocessing.format_structured_summary(
                    self, summary_text, text, keywords
                ),
            )

            result: SummarizerResult = {
                "summary": structured_summary,
                "method": method,
                "input_length": len(text),
                "backend": self.backend,
                "strategy": self.strategy,
                "warnings": [],
                "audit": {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "duration_sec": round(duration, 2),
                    "input_tokens": len(text.split()),
                    "output_tokens": len(summary_text.split()),
                    "chunks_processed": (len(text) + self.chunk_size - 1)
                    // self.chunk_size,
                },
            }

            # Post-hook
            if self.post_hook:
                try:
                    result = cast(SummarizerResult, self.post_hook(context, result))
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
                    result["warnings"].append(f"Post-hook failed: {e!s}")

            # Cache the result
            if self._cache is not None:
                self._cache[cache_key] = result
                self.logger_manager.log_metric(
                    "cache_stores", 1, MetricType.COUNTER, tags={"stage": "cache_store"}
                )

            self.logger.info(
                "Summarization completed successfully",
                extra={
                    "context": {
                        "stage": "completion",
                        "output_keys": list(result.keys()),
                        "summary_length": sum(
                            len(str(v))
                            for v in result["summary"].values()
                            if isinstance(v, (str, list))
                        ),
                    }
                },
            )
            return cast(SummarizerResult, result)

    @staticmethod
    def _extract_text(context: dict[str, Any]) -> str:
        """Extract text from context, handling both direct and nested cases."""
        text = context.get("text", "")
        if not text and "file_extraction" in context:
            file_extraction = context["file_extraction"]
            if isinstance(file_extraction, dict) and "text" in file_extraction:
                text = file_extraction["text"]
        return text if isinstance(text, str) else ""

    def _extract_keywords(self, text: str, task_goal: str) -> list[str]:
        """Extract keywords dynamically from the task goal and text.

        Args:
            text: The input text to analyze.
            task_goal: The task goal string to guide keyword extraction.

        Returns:
            List of keywords relevant to the task.
        """
        # Extract words from task goal
        task_words = task_goal.lower().split()
        task_keywords = [
            word for word in task_words if len(word) >= self.min_keyword_length
        ]

        # Extract frequent words from text
        words = re.findall(r"\b\w+\b", text.lower())
        words = [
            word
            for word in words
            if len(word) >= self.min_keyword_length and word.isalpha()
        ]
        word_counts = Counter(words)
        common_words = [
            word for word, count in word_counts.most_common(self.top_keywords_count)
        ]

        # Combine and prioritize task goal keywords
        keywords = task_keywords + common_words
        keywords = list(dict.fromkeys(keywords))  # Remove duplicates
        keywords = keywords[: self.top_keywords_count]  # Limit number of keywords

        self.logger.debug(
            "Extracted keywords",
            extra={"context": {"keywords": keywords}},
        )
        return keywords

    async def _summarize(
        self, text: str, prompt_prefix: str, task_goal: str, keywords: list[str]
    ) -> tuple[str, str]:
        """Summarize using the configured strategy with section awareness.

        Args:
            text: Text to summarize.
            prompt_prefix: Optional prompt prefix for revision.
            task_goal: Task goal to guide summarization focus.
            keywords: List of keywords to prioritize relevant content.

        Returns:
            Tuple of (summary text, method used).
        """
        method = f"{self.strategy}_{self.backend}"

        # Parse sections for section-aware summarization
        sections = extractive.parse_sections(self, text, keywords)
        self.logger.debug(
            f"Parsed {len(sections)} sections",
            extra={"context": {"sections": [s["heading"] for s in sections]}},
        )

        # Summarize based on strategy
        if self.strategy == self.STRATEGY_EXTRACTIVE:
            summary = extractive.generate_extractive_summary(self, sections, keywords)
        elif self.strategy == self.STRATEGY_ABSTRACTIVE:
            summary = await abstractive.generate_abstractive_summary(
                self, sections, prompt_prefix, task_goal, keywords
            )
        else:  # Hybrid
            extractive_summary = extractive.generate_extractive_summary(
                self, sections, keywords
            )
            abstractive_summary = await abstractive.generate_abstractive_summary(
                self, sections, prompt_prefix, task_goal, keywords
            )
            summary = postprocessing.combine_summaries(
                self, extractive_summary, abstractive_summary
            )

        self.logger.debug(
            "Summarization strategy applied",
            extra={
                "context": {
                    "strategy": self.strategy,
                    "method": method,
                    "summary_length": len(summary),
                }
            },
        )
        return summary, method

    def _revise_payload(
        self, feedback: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Adjust summarization settings based on feedback."""
        self.logger.info(
            "Revising summary based on feedback",
            extra={"context": {"feedback": feedback}},
        )

        # Adjust summarization parameters based on feedback
        if isinstance(feedback, dict) and "message" in feedback:
            message = str(feedback["message"]).lower()
            if "too short" in message:
                self.max_length = int(self.max_length * 1.2)
            if "too long" in message:
                self.max_length = int(self.max_length * 0.8)
            if self.strategy == self.STRATEGY_HYBRID and (
                "missing" in message or "incomplete" in message
            ):
                self.strategy_weights[self.STRATEGY_ABSTRACTIVE] += 0.1
                self.strategy_weights[self.STRATEGY_EXTRACTIVE] -= 0.1
                total = sum(self.strategy_weights.values())
                for key in self.strategy_weights:
                    self.strategy_weights[key] /= total

        updated = dict(context)
        updated["feedback"] = feedback.get("message", "")
        return updated

    def error_payload(
        self,
        msg: str,
        context: dict[str, Any],
        stage: str,
        extra: dict[str, Any] | None = None,
    ) -> SummarizerErrorResult:
        """Build a standardized error payload for summarization."""
        _ = extra
        return {
            "error": msg,
            "stage": stage,
            "input": context or {},
            "summary": {
                "executive_summary": "Error occurred during summarization.",
                "key_points": ["- N/A"],
                "actionable_insights": "N/A",
                "critical_risks": "Unable to assess due to error.",
                "missing_info": "Summary not generated.",
            },
            "method": "",
            "input_length": len(self._extract_text(context)),
            "backend": self.backend,
            "strategy": self.strategy,
            "warnings": [],
            "audit": {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "duration_sec": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
                "chunks_processed": 0,
            },
        }

    @classmethod
    def self_report_schema(cls) -> dict[str, Any]:
        """Return the output schema for documentation and validation."""
        return {
            "summary": {
                "executive_summary": "str",
                "key_points": "list[str]",
                "actionable_insights": "str",
                "critical_risks": "str",
                "missing_info": "str",
            },
            "method": "str",
            "input_length": "int",
            "backend": "str",
            "strategy": "str",
            "warnings": "list[str]",
            "audit": {
                "timestamp": "str",
                "duration_sec": "float",
                "input_tokens": "int",
                "output_tokens": "int",
                "chunks_processed": "int",
            },
        }

    @classmethod
    def coverage_report(cls, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Describe the parts of the context this agent consumes or modifies."""
        return {
            "consumes": ["text", "file_extraction", "feedback", "task_goal"],
            "modifies": [],
            "produces": ["summary"],
        }

    async def get_telemetry(self) -> dict[str, dict[str, Any]]:
        """Retrieve telemetry metrics."""
        try:
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

    async def shutdown(self) -> None:
        """Shutdown the agent and flush logs."""
        self.logger.info(
            "Shutting down SummarizerAgent",
            extra={"context": {"stage": "shutdown"}},
        )
        self.logger_manager.flush()
        self.logger.info(
            "SummarizerAgent shutdown complete",
            extra={"context": {"stage": "shutdown"}},
        )
        await super().shutdown()
