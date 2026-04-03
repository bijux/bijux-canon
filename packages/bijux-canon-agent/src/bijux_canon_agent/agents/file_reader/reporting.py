"""Reporting helpers for the file reader agent."""

from __future__ import annotations

from pathlib import Path
import time
from typing import Any


def build_file_agent_audit(
    file_path: str,
    *,
    agent_version: str,
    agent_id: str,
    cache_enabled: bool,
    async_io: bool,
    context_id: str,
    file_type: str | None = None,
) -> dict[str, Any]:
    """Build the durable audit payload for a file reader result."""
    resolved_file_type = file_type or Path(file_path).suffix.lstrip(".").lower()
    return {
        "file_path": str(file_path),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "agent_version": agent_version,
        "agent_id": agent_id,
        "cache_enabled": cache_enabled,
        "async_io": async_io,
        "context_id": context_id,
        "file_type": resolved_file_type,
    }


def build_file_reader_error_payload(
    msg: str,
    context: dict[str, Any],
    stage: str,
    *,
    attempt: int,
    agent_version: str,
    agent_id: str,
    cache_enabled: bool,
    async_io: bool,
) -> dict[str, Any]:
    """Return a standardized file reader error payload."""
    file_path = str(context.get("file_path", "unknown"))
    return {
        "error": msg,
        "stage": stage,
        "input": context,
        "attempt": attempt,
        "file_info": {},
        "structure_preview": {},
        "enrichments": {},
        "file_agent_audit": build_file_agent_audit(
            file_path,
            agent_version=agent_version,
            agent_id=agent_id,
            cache_enabled=cache_enabled,
            async_io=async_io,
            context_id=str(context.get("context_id", "unknown")),
        ),
        "cache_hit": False,
        "action_plan": [f"Fix file read error: {msg}"],
    }


def build_self_report_schema() -> dict[str, Any]:
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


def build_coverage_report() -> dict[str, Any]:
    """Describe the parts of the context the file reader consumes or produces."""
    return {
        "consumes": ["file_path"],
        "modifies": [],
        "produces": [
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
        ],
    }


__all__ = [
    "build_coverage_report",
    "build_file_agent_audit",
    "build_file_reader_error_payload",
    "build_self_report_schema",
]
