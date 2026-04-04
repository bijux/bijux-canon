"""Result and telemetry helpers for the summarizer agent."""

from __future__ import annotations

import time
from typing import Any

from bijux_canon_agent.observability.logging import LoggerManager, MetricType


def build_summarizer_result(
    *,
    structured_summary: dict[str, Any],
    method: str,
    text: str,
    backend: str,
    strategy: str,
    chunk_size: int,
    duration: float,
) -> dict[str, Any]:
    """Build the canonical summarizer result payload."""
    return {
        "summary": structured_summary,
        "method": method,
        "input_length": len(text),
        "backend": backend,
        "strategy": strategy,
        "warnings": [],
        "audit": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "duration_sec": round(duration, 2),
            "input_tokens": len(text.split()),
            "output_tokens": len(
                " ".join(_summary_text_parts(structured_summary)).split()
            ),
            "chunks_processed": (len(text) + chunk_size - 1) // chunk_size,
        },
    }


def build_summarizer_error_result(
    msg: str,
    context: dict[str, Any],
    *,
    input_length: int,
    backend: str,
    strategy: str,
) -> dict[str, Any]:
    """Build a standardized summarizer error payload."""
    return {
        "error": msg,
        "stage": context.get("stage", ""),
        "input": context or {},
        "summary": {
            "executive_summary": "Error occurred during summarization.",
            "key_points": ["- N/A"],
            "actionable_insights": "N/A",
            "critical_risks": "Unable to assess due to error.",
            "missing_info": "Summary not generated.",
        },
        "method": "",
        "input_length": input_length,
        "backend": backend,
        "strategy": strategy,
        "warnings": [],
        "audit": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "duration_sec": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "chunks_processed": 0,
        },
    }


def build_summarizer_schema() -> dict[str, Any]:
    """Return the summarizer output schema."""
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


def build_summarizer_coverage_report() -> dict[str, Any]:
    """Describe summarizer context boundaries."""
    return {
        "consumes": ["text", "file_extraction", "feedback", "task_goal"],
        "modifies": [],
        "produces": ["summary"],
    }


async def get_summarizer_telemetry(
    *,
    logger: Any,
    logger_manager: LoggerManager,
) -> dict[str, dict[str, Any]]:
    """Retrieve summarizer telemetry with consistent logging."""
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


def _summary_text_parts(structured_summary: dict[str, Any]) -> list[str]:
    parts: list[str] = []
    for value in structured_summary.values():
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(str(item) for item in value)
    return parts


__all__ = [
    "build_summarizer_coverage_report",
    "build_summarizer_error_result",
    "build_summarizer_result",
    "build_summarizer_schema",
    "get_summarizer_telemetry",
]
