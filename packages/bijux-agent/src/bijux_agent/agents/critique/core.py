"""CritiqueAgent module for Bijux Agent.

This module provides the CritiqueAgent class for evaluating AI-generated outputs.
"""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import time
from typing import Any, ClassVar, cast

from bijux_agent.agents.base import BaseAgent
from bijux_agent.utilities.logger_manager import LoggerManager

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

            # Preprocess context
            if self.pre_hook:
                try:
                    context = self.pre_hook(context)
                except Exception as e:
                    error_msg = f"Pre-hook failed: {e!s}"
                return await self.execution_kernel.error_result(
                    error_msg,
                    context,
                    "pre_hook",
                    {"context": str(context)[:1000]},
                )

            # Extract text with improved handling for summaries
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

            source_text = context.get("source_text", context.get("text", ""))
            cache_key = hashlib.sha256(text.encode()).hexdigest()

            # Check cache
            if self._cache is not None and cache_key in self._cache:
                self.logger.debug(
                    "Returning cached critique result",
                    extra={"context": {"cache_key": cache_key}},
                )
                return self._cache[cache_key]

            # Perform critique with retry mechanism
            start_time = time.perf_counter()
            result: dict[str, Any] | None = None
            for attempt in range(self.max_retries + 1):
                try:
                    result = await self._perform_critique(text, context, source_text)
                    break
                except Exception as e:
                    error_msg = (
                        f"Critique attempt {attempt + 1}/{self.max_retries + 1} "
                        f"failed: {e!s}"
                    )
                    self.logger.error(
                        error_msg,
                        extra={"context": {"stage": "perform_critique"}},
                    )
                    if attempt == self.max_retries:
                        error_msg = (
                            f"Critique failed after {self.max_retries + 1} "
                            f"attempts: {e!s}"
                        )
                        return await self.execution_kernel.error_result(
                            error_msg,
                            context,
                            "perform_critique",
                            {"context": str(context)[:1000]},
                        )

            duration = time.perf_counter() - start_time

            # Post-process result
            if self.post_hook:
                try:
                    if result is None:
                        raise RuntimeError("Critique process produced no result")
                    result = cast(CritiqueResult, self.post_hook(context, result))
                except Exception as e:
                    error_msg = f"Post-hook failed: {e!s}"
                    return await self.execution_kernel.error_result(
                        error_msg,
                        context,
                        "post_hook",
                        {"context": str(context)[:1000]},
                    )

            if result is None:
                raise RuntimeError("Critique process produced no result")

            critique_result = cast(CritiqueResult, result)
            formatted_result = self._format_critique_output(
                critique_result, text, source_text
            )

            if self._cache is not None:
                self._cache[cache_key] = formatted_result

            self._log_critique_completion(critique_result, duration)
            return formatted_result

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
        per_critique, warnings, issues = [], [], []
        score = 1.0

        # Early exit for empty text
        if not text.strip():
            per_critique.append(
                self._create_result(self.Criteria.NOT_EMPTY, False, ["Text is empty"])
            )
            return await self._final_report(
                "needs_revision",
                0.0,
                per_critique,
                warnings,
                issues,
            )

        # Evaluate criteria
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
            except Exception as e:
                error_msg = f"Check failed: {e!s}"
                per_critique.append(
                    self._create_result(crit, False, [error_msg], severity="Critical")
                )
                score -= self.penalties.get(crit, 0.1)
                issues.append(f"Criterion {crit} failed: {e!s}")

        # LLM and custom checks
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
        # LLM-augmented checks
        if self.llm_critique_fn:
            for crit in [self.Criteria.NO_HALLUCINATION, self.Criteria.NO_UNSUPPORTED]:
                if crit in self.criteria:
                    for attempt in range(self.max_retries + 1):
                        try:
                            llm_result = await self.llm_critique_fn(
                                text,
                                {**context, "check": crit},
                            )
                            if llm_result.get("result") == "FAIL":
                                score -= self.penalties.get(crit, 0.3)
                                per_critique.append(
                                    CriterionResult(
                                        name=crit,
                                        result="FAIL",
                                        issues=llm_result.get("issues", []),
                                        suggestion=self.suggestion_map[crit],
                                        severity=self.severity_map[crit],
                                        confidence=llm_result.get("confidence", 1.0),
                                    )
                                )
                                issues.extend(llm_result.get("issues", []))
                            confidence = llm_result.get("confidence", 1.0)
                            if confidence < 0.7:
                                warnings.append(
                                    f"Low confidence for LLM check '{crit}': "
                                    f"{confidence}"
                                )
                            break
                        except Exception as e:
                            error_msg = (
                                f"LLM critique for '{crit}' attempt "
                                f"{attempt + 1}/{self.max_retries + 1} failed: {e!s}"
                            )
                            self.logger.error(
                                error_msg,
                                extra={"context": {"stage": "llm_critique"}},
                            )
                            if attempt == self.max_retries:
                                error_msg = (
                                    f"LLM critique for '{crit}' failed after retries: "
                                    f"{e!s}"
                                )
                                warnings.append(error_msg)

        # Custom checks
        if self.custom_checks:
            for attempt in range(self.max_retries + 1):
                try:
                    custom_issues = await self.custom_checks(text, context) or []
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
                    break
                except Exception as e:
                    error_msg = (
                        f"Custom checks attempt {attempt + 1}/"
                        f"{self.max_retries + 1} failed: {e!s}"
                    )
                    self.logger.error(
                        error_msg,
                        extra={"context": {"stage": "custom_checks"}},
                    )
                    if attempt == self.max_retries:
                        warnings.append(f"Custom checks failed after retries: {e!s}")

        return score, per_critique, warnings, issues

    def _format_critique_output(
        self,
        result: CritiqueResult,
        summary: str,
        source_text: str,
    ) -> dict[str, Any]:
        """Format the critique output with detailed feedback."""
        scores = {
            "accuracy": 5,
            "completeness": 5,
            "clarity": 5,
            "brevity": 5,
            "critical_tone": 5,
            "relevance": 5,  # Added relevance score
        }
        strengths, weaknesses = [], []

        overall_score = int(result["score"] * 5)
        for key in scores:
            scores[key] = overall_score

        for crit in result["per_criterion"]:
            crit_name = crit["name"]
            if crit["result"] == "PASS":
                strengths.append(
                    f"Criterion '{crit_name}' passed: Meets expectations "
                    f"(Confidence: {crit['confidence']})."
                )
            else:
                if crit_name == self.Criteria.NO_HALLUCINATION and source_text:
                    issue_text = crit["issues"][0].lower()
                    if not any(
                        word in source_text.lower() for word in issue_text.split()
                    ):
                        weaknesses.append(
                            f"Hallucination: '{issue_text}' not in source "
                            f"(Confidence: {crit['confidence']})."
                        )
                    else:
                        weaknesses.append(
                            f"Criterion '{crit_name}' failed: {crit['issues'][0]} "
                            f"(Confidence: {crit['confidence']})."
                        )
                elif crit_name == self.Criteria.RELEVANCE:
                    weaknesses.append(
                        f"Relevance issue: {crit['issues'][0]} "
                        f"(Confidence: {crit['confidence']})."
                    )
                else:
                    weaknesses.append(
                        f"Criterion '{crit_name}' failed: {crit['issues'][0]} "
                        f"(Confidence: {crit['confidence']})."
                    )

                self._adjust_scores(crit_name, scores)

        for key in scores:
            scores[key] = max(0, min(5, scores[key]))

        return self._finalize_critique_output(scores, strengths, weaknesses, result)

    def _adjust_scores(self, crit_name: str, scores: dict[str, int]) -> None:
        """Adjust critique scores based on specific failures."""
        if crit_name == self.Criteria.NOT_EMPTY:
            scores["completeness"] -= 2
        elif crit_name == self.Criteria.NO_HALLUCINATION:
            scores["accuracy"] -= 2
        elif crit_name == self.Criteria.NO_REPETITION:
            scores["clarity"] -= 1
        elif crit_name == self.Criteria.LENGTH_REASONABLE:
            scores["brevity"] -= 1
        elif (
            crit_name == self.Criteria.FORMATTING_BASIC
            or crit_name == self.Criteria.PUNCTUATION_EXCESSIVE
        ):
            scores["clarity"] -= 1
        elif crit_name == self.Criteria.NO_UNSUPPORTED:
            scores["critical_tone"] -= 1
        elif crit_name == self.Criteria.RELEVANCE:
            scores["relevance"] -= 2
            scores["completeness"] -= 1

    def _finalize_critique_output(
        self,
        scores: dict[str, int],
        strengths: list[str],
        weaknesses: list[str],
        result: CritiqueResult,
    ) -> dict[str, Any]:
        """Finalize the critique output with quality assessment."""
        avg_score = sum(scores.values()) / len(scores)
        final_quality = (
            "OUTSTANDING"
            if avg_score >= 4.5
            else (
                "GOOD"
                if avg_score >= 3.5
                else (
                    "OK" if avg_score >= 2.5 else "POOR" if avg_score >= 1.5 else "FAIL"
                )
            )
        )

        hallucination_flag = any(
            crit["name"] == self.Criteria.NO_HALLUCINATION and crit["result"] == "FAIL"
            for crit in result["per_criterion"]
        )
        missing_info_flag = any(
            crit["name"] == self.Criteria.NOT_EMPTY and crit["result"] == "FAIL"
            for crit in result["per_criterion"]
        )
        relevance_flag = any(
            crit["name"] == self.Criteria.RELEVANCE and crit["result"] == "FAIL"
            for crit in result["per_criterion"]
        )

        if len(strengths) < 2:
            strengths.extend(
                ["No additional strengths identified."] * (2 - len(strengths))
            )
        if len(weaknesses) < 2:
            weaknesses.extend(
                ["No additional weaknesses identified."] * (2 - len(weaknesses))
            )

        return {
            "critique_status": result["critique_status"],
            "score": result["score"],
            "per_criterion": result["per_criterion"],
            "warnings": result["warnings"],
            "issues": result["issues"],
            "criteria": result["criteria"],
            "action_plan": result["action_plan"],
            "audit": result["audit"],
            "scores": scores,
            "strengths": strengths[:2],
            "weaknesses": weaknesses[:2],
            "hallucination_flag": hallucination_flag,
            "missing_info_flag": missing_info_flag,
            "relevance_flag": relevance_flag,  # Added relevance flag
            "final_quality": final_quality,
        }

    def _create_result(
        self,
        name: str,
        passed: bool,
        issues: list[str],
        severity: str | None = None,
        confidence: float = 1.0,
    ) -> CriterionResult:
        """Create a CriterionResult object with confidence."""
        return CriterionResult(
            name=name,
            result="PASS" if passed else "FAIL",
            issues=issues,
            suggestion=self.suggestion_map[name] if not passed else "",
            severity=severity or self.severity_map[name] if not passed else "",
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
        fails = [c for c in per_critique if c.result == "FAIL"]
        fails_sorted = sorted(
            fails,
            key=lambda x: {"Critical": 1, "Major": 2, "Minor": 3}.get(x.severity, 4),
        )
        action_plan = [
            f"{c.severity}: {c.suggestion} (Issue: {', '.join(c.issues)}, "
            f"Confidence: {c.confidence})"
            for c in fails_sorted
        ]

        # Add specific guidance for relevance failures
        for crit in fails_sorted:
            if crit.name == self.Criteria.RELEVANCE:
                missing_topics = (
                    crit.issues[0].split(": ")[1]
                    if ": " in crit.issues[0]
                    else crit.issues[0]
                )
                action_plan.append(
                    f"Critical: Focus on including details about {missing_topics} "
                    "in the summary."
                )

        final_result: CritiqueResult = {
            "critique_status": status,
            "score": score,
            "per_criterion": [vars(c) for c in per_critique],
            "warnings": warnings,
            "issues": issues,
            "criteria": self.criteria,
            "action_plan": action_plan,
            "audit": {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "shards_merged": 1,
            },
        }
        return final_result

    def error_payload(
        self,
        msg: str,
        context: dict[str, Any],
        stage: str,
        extra: dict[str, Any] | None = None,
    ) -> CritiqueResult:
        """Return a standardized error result with detailed logging."""
        _ = (context, stage, extra)
        return {
            "critique_status": "failed",
            "score": 0.0,
            "per_criterion": [],
            "warnings": [msg],
            "issues": [msg],
            "criteria": self.criteria,
            "action_plan": [],
            "audit": {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "shards_merged": 1,
            },
        }

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
        return {
            "critique": {
                "scores": dict.fromkeys(
                    [
                        "accuracy",
                        "completeness",
                        "clarity",
                        "brevity",
                        "critical_tone",
                        "relevance",
                    ],
                    "int (0-5)",
                ),
                "strengths": "list[str] (length 2)",
                "weaknesses": "list[str] (length 2)",
                "hallucination_flag": "bool",
                "missing_info_flag": "bool",
                "relevance_flag": "bool",
                "final_quality": "str (OUTSTANDING/GOOD/OK/POOR/FAIL)",
            }
        }

    @classmethod
    def coverage_report(
        cls,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Describe the parts of the context this agent consumes or modifies."""
        return {
            "consumes": [
                "summary",
                "text",
                "content",
                "source_text",
                "task_goal_keywords",
            ],
            "modifies": [],
            "produces": ["critique"],
        }

    def _log_critique_completion(self, result: CritiqueResult, duration: float) -> None:
        """Log the completion of the critique process with detailed metrics."""
        status = result.get("critique_status", "unknown")
        score = result.get("score", 0.0)
        issues = result.get("issues", [])
        warnings = result.get("warnings", [])
        self.logger.info(
            "Critique completed",
            extra={
                "context": {
                    "stage": "completion",
                    "status": status,
                    "score": score,
                    "duration_sec": duration,
                    "issues": issues,
                    "warnings": warnings,
                }
            },
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
