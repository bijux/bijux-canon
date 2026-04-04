"""CritiqueAgent module for Bijux Agent.

This module provides the CritiqueAgent class for evaluating AI-generated outputs.
"""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import time
from typing import Any, ClassVar, TypeAlias, cast

from bijux_canon_agent.agents.base import BaseAgent
from bijux_canon_agent.observability.logging import LoggerManager

from .reporting import (
    build_critique_coverage_report,
    build_critique_error_payload,
    build_critique_output,
    build_critique_schema,
    build_final_report,
    create_criterion_result,
    log_critique_completion,
)
from .rules import consistency, content, formatting
from .rules.types import (
    CriterionResult,
    CritiqueResult,
    CritiqueSeverity,
)


class CritiqueAgent(BaseAgent):
    """Enhanced CritiqueAgent for evaluating AI-generated outputs in Bijux Agent.

    Provides actionable, high-quality feedback with robust error handling, relevance
    checking, and comprehensive logging for iterative improvement.
    """

    RULES: ClassVar[dict[str, Callable[..., CriterionResult]]] = {
        **consistency.RULES,
        **content.RULES,
        **formatting.RULES,
    }

    class Criteria:
        """Nested class defining critique criteria constants."""

        NOT_EMPTY = "not_empty"
        NO_REPETITION = "no_repetition"
        LENGTH_REASONABLE = "length_reasonable"
        FORMATTING_BASIC = "formatting_basic"
        NO_HALLUCINATION = "no_hallucination"
        NO_UNSUPPORTED = "no_unsupported_claims"
        PUNCTUATION_EXCESSIVE = "punctuation_excessive"
        CODE_SYNTAX = "code_syntax"
        RELEVANCE = "relevance"  # New criterion for task goal relevance

    DEFAULT_CRITERIA: ClassVar[list[str]] = [
        Criteria.NOT_EMPTY,
        Criteria.NO_REPETITION,
        Criteria.LENGTH_REASONABLE,
        Criteria.FORMATTING_BASIC,
        Criteria.NO_HALLUCINATION,
        Criteria.NO_UNSUPPORTED,
        Criteria.PUNCTUATION_EXCESSIVE,
        Criteria.RELEVANCE,  # Added relevance criterion
    ]

    DEFAULT_PENALTIES: ClassVar[dict[str, float]] = {
        Criteria.NOT_EMPTY: 0.5,
        Criteria.NO_REPETITION: 0.2,
        Criteria.LENGTH_REASONABLE: 0.1,
        Criteria.FORMATTING_BASIC: 0.1,
        Criteria.NO_HALLUCINATION: 0.3,
        Criteria.NO_UNSUPPORTED: 0.2,
        Criteria.PUNCTUATION_EXCESSIVE: 0.1,
        Criteria.CODE_SYNTAX: 0.3,
        Criteria.RELEVANCE: 0.4,  # High penalty for relevance failure
    }

    SEVERITY_MAP: ClassVar[dict[str, str]] = {
        Criteria.NOT_EMPTY: CritiqueSeverity.CRITICAL.value,
        Criteria.NO_REPETITION: CritiqueSeverity.MAJOR.value,
        Criteria.LENGTH_REASONABLE: CritiqueSeverity.MINOR.value,
        Criteria.FORMATTING_BASIC: CritiqueSeverity.MINOR.value,
        Criteria.NO_HALLUCINATION: CritiqueSeverity.CRITICAL.value,
        Criteria.NO_UNSUPPORTED: CritiqueSeverity.MAJOR.value,
        Criteria.PUNCTUATION_EXCESSIVE: CritiqueSeverity.MINOR.value,
        Criteria.CODE_SYNTAX: CritiqueSeverity.MAJOR.value,
        Criteria.RELEVANCE: CritiqueSeverity.CRITICAL.value,
    }

    SUGGESTION_MAP: ClassVar[dict[str, str]] = {
        Criteria.NOT_EMPTY: "Ensure the output is not empty.",
        Criteria.NO_REPETITION: "Reduce repeated phrases to improve clarity.",
        Criteria.LENGTH_REASONABLE: "Adjust length to be within bounds.",
        Criteria.FORMATTING_BASIC: "Fix formatting issues like extra spaces.",
        Criteria.NO_HALLUCINATION: "Remove content unrelated to the source.",
        Criteria.NO_UNSUPPORTED: "Provide citations to support all claims.",
        Criteria.PUNCTUATION_EXCESSIVE: "Remove excessive punctuation.",
        Criteria.CODE_SYNTAX: "Correct syntax errors in code blocks.",
        Criteria.RELEVANCE: "Ensure the summary addresses all required topics.",
    }

    AdvancedCheckState: TypeAlias = tuple[
        float,
        list[CriterionResult],
        list[str],
        list[str],
    ]

    def __init__(
        self,
        config: dict[str, Any],
        logger_manager: LoggerManager,
        pre_hook: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        post_hook: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
        | None = None,
    ):
        """Initialize the CritiqueAgent with configuration and logger manager."""
        super().__init__(config, logger_manager)
        self.pre_hook = pre_hook
        self.post_hook = post_hook

        # Configuration settings
        self.criteria = list(self.config.get("criteria", self.DEFAULT_CRITERIA))
        self.penalties = dict(self.DEFAULT_PENALTIES)
        self.penalties.update(self.config.get("penalties", {}))
        self.severity_map = dict(self.SEVERITY_MAP)
        self.suggestion_map = dict(self.SUGGESTION_MAP)
        self.max_repetition = self.config.get("max_repetition", 3)
        self.repetition_ngram = self.config.get("repetition_ngram", 3)
        self.min_length = self.config.get("min_length", 20)
        self.max_length = self.config.get("max_length", 4096)
        self.llm_critique_fn = self.config.get("llm_critique_fn")
        self.custom_checks = self.config.get("custom_checks")
        self._cache: dict[str, dict[str, Any]] | None = (
            {} if self.config.get("enable_cache", True) else None
        )
        self.max_retries = self.config.get("max_retries", 2)  # For retry mechanism

        self._log_initialization()

    # Add the missing _initialize method
    def _initialize(self) -> None:
        """Initialize resources for CritiqueAgent.

        No additional initialization is required beyond what is done in __init__.
        """
        pass

    # Add the missing _cleanup method
    def _cleanup(self) -> None:
        """Clean up resources used by CritiqueAgent.

        Clears the cache if it exists.
        """
        if self._cache is not None:
            self._cache.clear()
            self.logger.debug(
                "Cache cleared during cleanup",
                extra={"context": {"stage": "cleanup"}},
            )

    # Add the capabilities property
    @property
    def capabilities(self) -> list[str]:
        """List of capabilities this agent supports.

        Returns:
            A list of capabilities, specifically ["critique"] for this agent.
        """
        return ["critique"]

    def _log_initialization(self) -> None:
        """Log the initialization details of the CritiqueAgent."""
        self.logger.info(
            "CritiqueAgent initialized",
            extra={
                "context": {
                    "criteria": self.criteria,
                    "config": {
                        "max_repetition": self.max_repetition,
                        "repetition_ngram": self.repetition_ngram,
                        "min_length": self.min_length,
                        "max_length": self.max_length,
                        "enable_cache": bool(self._cache),
                        "has_llm_critique_fn": self.llm_critique_fn is not None,
                        "has_custom_checks": self.custom_checks is not None,
                        "max_retries": self.max_retries,
                    },
                }
            },
        )
        self._configure_criteria(self.config.get("context", {}))

    def _configure_criteria(self, context: dict[str, Any]) -> None:
        """Configure criteria based on the input context (e.g., text type)."""
        text_type = context.get("text_type", "general")
        if text_type == "tweet":
            self.max_length = 280
            self.penalties[self.Criteria.LENGTH_REASONABLE] = 0.3
            self.penalties[self.Criteria.NO_REPETITION] = 0.25
        elif text_type == "article":
            self.min_length = 200
            self.penalties[self.Criteria.NO_UNSUPPORTED] = 0.4
            self.penalties[self.Criteria.NO_HALLUCINATION] = 0.4
        elif text_type == "code":
            if self.Criteria.CODE_SYNTAX not in self.criteria:
                self.criteria.append(self.Criteria.CODE_SYNTAX)

        self.logger.debug(
            f"Configured criteria for text_type: {text_type}",
            extra={
                "context": {
                    "min_length": self.min_length,
                    "max_length": self.max_length,
                    "updated_penalties": self.penalties,
                }
            },
        )

    async def _run_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        """Critique the provided text and return feedback."""
        context_id = context.get("context_id", "unknown")
        with self.logger.context(agent="CritiqueAgent", context_id=context_id):
            self.logger.info("Starting critique", extra={"context": {"stage": "init"}})

            prepared_context, pre_hook_error = self._apply_pre_hook(context)
            if pre_hook_error is not None:
                return await self.execution_kernel.error_result(
                    pre_hook_error,
                    context,
                    "pre_hook",
                    {"context": str(context)[:1000]},
                )
            context = prepared_context

            text = self._extract_text(context)
            if text is None:
                error_msg = (
                    "Text must be a string. Ensure 'summary', 'text', or 'content' "
                    "is a string."
                )
                return await self.execution_kernel.error_result(
                    error_msg,
                    context,
                    "input_validation",
                    {"context": str(context)[:1000]},
                )

            source_text = self._source_text(context)
            cache_key = hashlib.sha256(text.encode()).hexdigest()
            cached_result = self._cached_result(cache_key)
            if cached_result is not None:
                return cached_result
            start_time = time.perf_counter()
            result = await self._perform_critique_with_retries(
                text,
                context,
                source_text,
            )
            if result is None:
                return await self.execution_kernel.error_result(
                    f"Critique failed after {self.max_retries + 1} attempts",
                    context,
                    "perform_critique",
                    {"context": str(context)[:1000]},
                )
            duration = time.perf_counter() - start_time
            critique_result = self._apply_post_hook(context, result)
            if critique_result is None:
                return await self.execution_kernel.error_result(
                    "Post-hook failed",
                    context,
                    "post_hook",
                    {"context": str(context)[:1000]},
                )
            formatted_result = self._format_critique_output(
                critique_result, text, source_text
            )
            self._store_cached_result(cache_key, formatted_result)
            self._log_critique_completion(critique_result, duration)
            return formatted_result

    def _apply_pre_hook(
        self, context: dict[str, Any]
    ) -> tuple[dict[str, Any], str | None]:
        """Apply the optional pre-hook and return the updated context."""
        if not self.pre_hook:
            return context, None
        try:
            return self.pre_hook(context), None
        except Exception as exc:
            return context, f"Pre-hook failed: {exc!s}"

    @staticmethod
    def _source_text(context: dict[str, Any]) -> str:
        """Return the source text fallback chain for critique reporting."""
        return str(context.get("source_text", context.get("text", "")))

    def _cached_result(self, cache_key: str) -> dict[str, Any] | None:
        """Return a cached critique result when available."""
        if self._cache is None or cache_key not in self._cache:
            return None
        self.logger.debug(
            "Returning cached critique result",
            extra={"context": {"cache_key": cache_key}},
        )
        return self._cache[cache_key]

    def _store_cached_result(
        self, cache_key: str, formatted_result: dict[str, Any]
    ) -> None:
        """Store the formatted critique result in cache when enabled."""
        if self._cache is not None:
            self._cache[cache_key] = formatted_result

    async def _perform_critique_with_retries(
        self,
        text: str,
        context: dict[str, Any],
        source_text: str,
    ) -> CritiqueResult | None:
        """Retry critique execution until success or retry exhaustion."""
        for attempt in range(self.max_retries + 1):
            try:
                return await self._perform_critique(text, context, source_text)
            except Exception as exc:
                error_msg = (
                    f"Critique attempt {attempt + 1}/{self.max_retries + 1} "
                    f"failed: {exc!s}"
                )
                self.logger.error(
                    error_msg,
                    extra={"context": {"stage": "perform_critique"}},
                )
        return None

    def _apply_post_hook(
        self,
        context: dict[str, Any],
        result: CritiqueResult,
    ) -> CritiqueResult | None:
        """Apply the optional post-hook to the critique result."""
        if not self.post_hook:
            return result
        try:
            return cast(CritiqueResult, self.post_hook(context, result))
        except Exception as exc:
            self.logger.error(
                f"Post-hook failed: {exc!s}",
                extra={"context": {"stage": "post_hook"}},
            )
            return None

    @staticmethod
    def _extract_text(context: dict[str, Any]) -> str | None:
        """Extract text from context with improved handling for summary dictionaries."""
        # Handle dictionary input (e.g., summary with executive_summary, key_points)
        if isinstance(context.get("summary"), dict):
            summary_dict = context["summary"]
            text_parts = []
            for key in ["executive_summary", "key_points", "content", "text"]:
                if key in summary_dict:
                    value = summary_dict[key]
                    if isinstance(value, str):
                        text_parts.append(value)
                    elif isinstance(value, list):
                        text_parts.extend(
                            [str(item) for item in value if isinstance(item, str)]
                        )
            text = " ".join(text_parts) if text_parts else None
        else:
            # Fallback to original extraction logic
            text = (
                context.get("summary") or context.get("text") or context.get("content")
            )
            if text is None:
                text = str(context) if context else ""

        return text if isinstance(text, str) else None

    async def _perform_critique(
        self,
        text: str,
        context: dict[str, Any],
        source_text: str,
    ) -> dict[str, Any]:
        """Perform the critique evaluation with enhanced checks."""
        score, per_critique, warnings, issues = await self._evaluate_criteria(
            text, context
        )

        if not text.strip():
            return await self._final_report(
                "needs_revision",
                0.0,
                [
                    self._create_result(
                        self.Criteria.NOT_EMPTY,
                        False,
                        ["Text is empty"],
                    )
                ],
                [],
                [],
            )
        score, per_critique, warnings, issues = await self._run_advanced_checks(
            text,
            context,
            score,
            per_critique,
            warnings,
            issues,
        )

        score = round(max(0.0, min(1.0, score)), 3)
        status = "ok" if not issues else "needs_revision"
        return await self._final_report(status, score, per_critique, warnings, issues)

    async def _evaluate_criteria(
        self,
        text: str,
        context: dict[str, Any],
    ) -> AdvancedCheckState:
        """Evaluate the configured rule-backed critique criteria."""
        per_critique: list[CriterionResult] = []
        warnings: list[str] = []
        issues: list[str] = []
        score = 1.0
        for crit in self.criteria:
            check_fn = self.RULES.get(crit)
            if not check_fn:
                warnings.append(f"Criterion '{crit}' not implemented")
                continue
            try:
                result = check_fn(self, text, context)
                per_critique.append(result)
                if result.result == "FAIL":
                    score -= self.penalties.get(crit, 0.1)
                    issues.extend(result.issues)
            except Exception as exc:
                error_msg = f"Check failed: {exc!s}"
                per_critique.append(
                    self._create_result(crit, False, [error_msg], severity="Critical")
                )
                score -= self.penalties.get(crit, 0.1)
                issues.append(f"Criterion {crit} failed: {exc!s}")
        return score, per_critique, warnings, issues

    async def _run_advanced_checks(
        self,
        text: str,
        context: dict[str, Any],
        score: float,
        per_critique: list[CriterionResult],
        warnings: list[str],
        issues: list[str],
    ) -> tuple[float, list[CriterionResult], list[str], list[str]]:
        """Run LLM-augmented and custom checks with improved handling."""
        score, per_critique, warnings, issues = await self._run_llm_checks(
            text,
            context,
            score,
            per_critique,
            warnings,
            issues,
        )
        return await self._run_custom_checks(
            text,
            context,
            score,
            per_critique,
            warnings,
            issues,
        )

    async def _run_llm_checks(
        self,
        text: str,
        context: dict[str, Any],
        score: float,
        per_critique: list[CriterionResult],
        warnings: list[str],
        issues: list[str],
    ) -> AdvancedCheckState:
        """Run retrying LLM-backed critique checks."""
        if not self.llm_critique_fn:
            return score, per_critique, warnings, issues
        for crit in [self.Criteria.NO_HALLUCINATION, self.Criteria.NO_UNSUPPORTED]:
            if crit not in self.criteria:
                continue
            llm_result = await self._run_llm_check_with_retries(text, context, crit)
            if llm_result is None:
                warnings.append(f"LLM critique for '{crit}' failed after retries")
                continue
            if llm_result.get("result") == "FAIL":
                score -= self.penalties.get(crit, 0.3)
                llm_issues = list(llm_result.get("issues", []))
                per_critique.append(
                    CriterionResult(
                        name=crit,
                        result="FAIL",
                        issues=llm_issues,
                        suggestion=self.suggestion_map[crit],
                        severity=self.severity_map[crit],
                        confidence=llm_result.get("confidence", 1.0),
                    )
                )
                issues.extend(llm_issues)
            confidence = float(llm_result.get("confidence", 1.0))
            if confidence < 0.7:
                warnings.append(f"Low confidence for LLM check '{crit}': {confidence}")
        return score, per_critique, warnings, issues

    async def _run_llm_check_with_retries(
        self,
        text: str,
        context: dict[str, Any],
        criterion: str,
    ) -> dict[str, Any] | None:
        """Run a single LLM-backed critique check with retries."""
        if not self.llm_critique_fn:
            return None
        for attempt in range(self.max_retries + 1):
            try:
                return await self.llm_critique_fn(
                    text,
                    {**context, "check": criterion},
                )
            except Exception as exc:
                self.logger.error(
                    f"LLM critique for '{criterion}' attempt "
                    f"{attempt + 1}/{self.max_retries + 1} failed: {exc!s}",
                    extra={"context": {"stage": "llm_critique"}},
                )
        return None

    async def _run_custom_checks(
        self,
        text: str,
        context: dict[str, Any],
        score: float,
        per_critique: list[CriterionResult],
        warnings: list[str],
        issues: list[str],
    ) -> AdvancedCheckState:
        """Run custom critique checks with retries."""
        if not self.custom_checks:
            return score, per_critique, warnings, issues
        custom_issues = await self._run_custom_checks_with_retries(text, context)
        if custom_issues is None:
            warnings.append("Custom checks failed after retries")
            return score, per_critique, warnings, issues
        if custom_issues:
            issues.extend(custom_issues)
            per_critique.append(
                CriterionResult(
                    name="custom",
                    result="FAIL",
                    issues=custom_issues,
                    suggestion="Resolve user-defined issues.",
                    severity=CritiqueSeverity.MAJOR.value,
                )
            )
            score -= 0.2
        return score, per_critique, warnings, issues

    async def _run_custom_checks_with_retries(
        self,
        text: str,
        context: dict[str, Any],
    ) -> list[str] | None:
        """Run custom checks until success or retry exhaustion."""
        if not self.custom_checks:
            return []
        for attempt in range(self.max_retries + 1):
            try:
                return list(await self.custom_checks(text, context) or [])
            except Exception as exc:
                self.logger.error(
                    f"Custom checks attempt {attempt + 1}/{self.max_retries + 1} "
                    f"failed: {exc!s}",
                    extra={"context": {"stage": "custom_checks"}},
                )
        return None

    def _format_critique_output(
        self,
        result: CritiqueResult,
        summary: str,
        source_text: str,
    ) -> dict[str, Any]:
        """Format the critique output with detailed feedback."""
        return build_critique_output(
            result,
            summary,
            source_text,
            criteria=self.Criteria,
        )

    def _create_result(
        self,
        name: str,
        passed: bool,
        issues: list[str],
        severity: str | None = None,
        confidence: float = 1.0,
    ) -> CriterionResult:
        """Create a CriterionResult object with confidence."""
        return create_criterion_result(
            name,
            passed,
            issues,
            suggestion_map=self.suggestion_map,
            severity_map=self.severity_map,
            severity=severity,
            confidence=confidence,
        )

    async def _final_report(
        self,
        status: str,
        score: float,
        per_critique: list[CriterionResult],
        warnings: list[str],
        issues: list[str],
    ) -> CritiqueResult:
        """Generate the final critique report with detailed action plan."""
        return await build_final_report(
            status,
            score,
            per_critique,
            warnings,
            issues,
            criteria=self.criteria,
            relevance_name=self.Criteria.RELEVANCE,
        )

    def error_payload(
        self,
        msg: str,
        context: dict[str, Any],
        stage: str,
        extra: dict[str, Any] | None = None,
    ) -> CritiqueResult:
        """Return a standardized error result with detailed logging."""
        _ = (context, stage, extra)
        return build_critique_error_payload(msg, self.criteria)

    def _revise_payload(
        self, feedback: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Revise critique settings based on feedback."""
        self.logger.info(
            "Revising critique based on feedback",
            extra={"context": {"feedback": feedback}},
        )
        if isinstance(feedback, dict) and "message" in feedback:
            message = str(feedback["message"]).lower()
            if "length" in message:
                self.penalties[self.Criteria.LENGTH_REASONABLE] += 0.1
            if "repetition" in message:
                self.max_repetition = max(1, self.max_repetition - 1)
            if "relevance" in message:
                self.penalties[self.Criteria.RELEVANCE] += 0.1

        return dict(context)

    @classmethod
    def self_report_schema(cls) -> dict[str, Any]:
        """Describe the agent's output schema for validation and composition."""
        return build_critique_schema()

    @classmethod
    def coverage_report(
        cls,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Describe the parts of the context this agent consumes or modifies."""
        return build_critique_coverage_report()

    def _log_critique_completion(self, result: CritiqueResult, duration: float) -> None:
        """Log the completion of the critique process with detailed metrics."""
        log_critique_completion(
            logger=self.logger,
            result=result,
            duration=duration,
        )

    async def shutdown(self) -> None:
        """Perform cleanup tasks during shutdown."""
        self.logger.info(
            "Shutting down CritiqueAgent",
            extra={"context": {"stage": "shutdown"}},
        )
        self.logger_manager.flush()
        self.logger.info(
            "CritiqueAgent shutdown complete",
            extra={"context": {"stage": "shutdown"}},
        )
        await super().shutdown()
