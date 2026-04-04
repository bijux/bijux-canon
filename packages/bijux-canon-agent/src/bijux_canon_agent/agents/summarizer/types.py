"""Typed payload contracts for the summarizer agent."""

from __future__ import annotations

from typing import Any, TypedDict


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


class SummaryRunInputs(TypedDict):
    """Run-time inputs assembled before summarization starts."""

    text: str
    task_goal: str
    keywords: list[str]
    cache_key: str
    prompt_prefix: str


__all__ = [
    "SummarizerAudit",
    "SummarizerErrorResult",
    "SummarizerResult",
    "SummarizerSummary",
    "SummaryRunInputs",
]
