"""Telemetry helpers for the file reader agent."""

from __future__ import annotations

from collections import Counter
import math
from pathlib import Path
from typing import Any

from bijux_canon_agent.observability.logging import LoggerManager, MetricType


def build_auto_enrichments(
    result: dict[str, Any],
    *,
    logger: Any,
    logger_manager: LoggerManager,
    agent_name: str,
) -> dict[str, Any]:
    """Generate automatic file reader enrichments and record related metrics."""
    enrich: dict[str, Any] = {}
    text = result.get("text", "")
    file_info = result.get("file_info", {})
    structure = result.get("structure_preview", {})
    file_path = file_info.get("file_path", "unknown") if file_info else "unknown"
    file_type = Path(file_path).suffix.lstrip(".").lower()
    tags = {
        "stage": "auto_enrichments",
        "agent": agent_name,
        "file_type": file_type,
    }

    _populate_text_enrichments(
        enrich,
        text,
        tags=tags,
        logger=logger,
        logger_manager=logger_manager,
    )
    _populate_file_metadata_enrichments(
        enrich,
        file_info,
        file_type=file_type,
        tags=tags,
        logger=logger,
        logger_manager=logger_manager,
    )
    _populate_structure_enrichments(
        enrich,
        structure,
        tags=tags,
        logger=logger,
        logger_manager=logger_manager,
    )
    return enrich


def _populate_text_enrichments(
    enrich: dict[str, Any],
    text: Any,
    *,
    tags: dict[str, str],
    logger: Any,
    logger_manager: LoggerManager,
) -> None:
    if not isinstance(text, str) or not text:
        return
    try:
        text_head = text[:400]
        text_tail = text[-200:] if len(text) > 600 else ""
        n_chars = len(text)
        n_lines = text.count("\n") + 1
        n_words = len(text.split())
        avg_word_length = sum(len(word) for word in text.split()) / max(n_words, 1)
        entropy = _text_entropy(text)
        text_complexity = _text_complexity(text)

        enrich["text_head"] = text_head
        enrich["text_tail"] = text_tail
        enrich["n_chars"] = n_chars
        enrich["n_lines"] = n_lines
        enrich["n_words"] = n_words
        enrich["avg_word_length"] = avg_word_length
        enrich["entropy"] = entropy
        enrich["text_complexity"] = text_complexity

        logger_manager.log_metric(
            "text_length_chars", n_chars, MetricType.GAUGE, tags=tags
        )
        logger_manager.log_metric("text_lines", n_lines, MetricType.GAUGE, tags=tags)
        logger_manager.log_metric("text_words", n_words, MetricType.GAUGE, tags=tags)
        logger_manager.log_metric(
            "avg_word_length",
            avg_word_length,
            MetricType.HISTOGRAM,
            tags=tags,
        )
        logger_manager.log_metric(
            "text_entropy",
            entropy,
            MetricType.HISTOGRAM,
            tags=tags,
        )
        logger_manager.log_metric(
            "text_complexity",
            text_complexity,
            MetricType.HISTOGRAM,
            tags=tags,
        )
        logger.debug(
            "Text enrichments computed",
            extra={
                "context": {
                    "stage": "auto_enrichments",
                    "metrics": {
                        "n_chars": n_chars,
                        "n_lines": n_lines,
                        "n_words": n_words,
                        "avg_word_length": avg_word_length,
                        "entropy": entropy,
                        "text_complexity": text_complexity,
                    },
                    "tags": tags,
                }
            },
        )
    except Exception as exc:
        logger.error(
            f"Text enrichment failed: {exc!s}",
            extra={
                "context": {
                    "stage": "auto_enrichments",
                    "error": str(exc),
                    "tags": tags,
                }
            },
        )
        logger_manager.log_metric(
            "text_enrichment_errors",
            1,
            MetricType.COUNTER,
            tags=tags,
        )


def _populate_file_metadata_enrichments(
    enrich: dict[str, Any],
    file_info: Any,
    *,
    file_type: str,
    tags: dict[str, str],
    logger: Any,
    logger_manager: LoggerManager,
) -> None:
    if not file_info:
        return
    try:
        file_size_bytes = file_info.get("file_size_bytes", 0)
        file_size_kb = round(file_size_bytes / 1024, 2)
        file_size_mb = round(file_size_kb / 1024, 2)
        enrich["file_size_kb"] = file_size_kb
        enrich["file_size_mb"] = file_size_mb
        enrich["file_type"] = file_info.get("file_type", file_type)
        enrich["last_modified"] = str(file_info.get("last_modified", ""))

        file_tags = {"file_type": enrich["file_type"], **tags}
        logger_manager.log_metric(
            "file_size_mb",
            file_size_mb,
            MetricType.GAUGE,
            tags=file_tags,
        )
        logger.debug(
            "File metadata enrichments computed",
            extra={
                "context": {
                    "stage": "auto_enrichments",
                    "metrics": {
                        "file_size_mb": file_size_mb,
                        "file_type": enrich["file_type"],
                    },
                    "tags": file_tags,
                }
            },
        )
    except Exception as exc:
        logger.error(
            f"File metadata enrichment failed: {exc!s}",
            extra={
                "context": {
                    "stage": "auto_enrichments",
                    "error": str(exc),
                    "tags": tags,
                }
            },
        )
        logger_manager.log_metric(
            "file_metadata_errors",
            1,
            MetricType.COUNTER,
            tags=tags,
        )


def _populate_structure_enrichments(
    enrich: dict[str, Any],
    structure: Any,
    *,
    tags: dict[str, str],
    logger: Any,
    logger_manager: LoggerManager,
) -> None:
    if not structure:
        return
    try:
        structure_sections = structure.get("sections", [])
        structure_tables = structure.get("tables", [])
        structure_images = structure.get("images", [])
        section_depths = [section.get("depth", 1) for section in structure_sections]
        max_section_depth = max(section_depths, default=1)
        enrich["structure_summary"] = {
            "n_sections": len(structure_sections),
            "has_tables": bool(structure_tables),
            "has_images": bool(structure_images),
            "max_section_depth": max_section_depth,
        }
        logger_manager.log_metric(
            "n_sections",
            enrich["structure_summary"]["n_sections"],
            MetricType.GAUGE,
            tags=tags,
        )
        logger_manager.log_metric(
            "max_section_depth",
            enrich["structure_summary"]["max_section_depth"],
            MetricType.GAUGE,
            tags=tags,
        )
        logger.debug(
            "Structure summary computed",
            extra={
                "context": {
                    "stage": "auto_enrichments",
                    "structure_summary": enrich["structure_summary"],
                    "tags": tags,
                }
            },
        )
    except Exception as exc:
        logger.error(
            f"Structure enrichment failed: {exc!s}",
            extra={
                "context": {
                    "stage": "auto_enrichments",
                    "error": str(exc),
                    "tags": tags,
                }
            },
        )
        logger_manager.log_metric(
            "structure_enrichment_errors",
            1,
            MetricType.COUNTER,
            tags=tags,
        )


def _text_entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = Counter(text)
    total = len(text)
    return round(
        -sum((count / total) * math.log2(count / total) for count in counts.values()), 4
    )


def _text_complexity(text: str) -> float:
    if not text:
        return 0.0
    words = [word for word in text.split() if word.strip()]
    if not words:
        return 0.0
    avg_word_length = sum(len(word) for word in words) / len(words)
    unique_words = len(set(words))
    return round(avg_word_length * (unique_words / len(words)), 2)


__all__ = [
    "build_auto_enrichments",
]
