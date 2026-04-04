"""Lifecycle helpers for universal file reading."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
import time
from typing import Any

from .structure_preview import create_structure_preview

FileAuditFactory = Callable[[str | Path], Awaitable[dict[str, Any]]]


async def validate_read_target(
    file_path: Path,
    *,
    max_file_bytes: int,
    create_file_audit: FileAuditFactory,
) -> dict[str, Any] | None:
    """Return a standardized error payload when the read target is invalid."""
    if not file_path.exists():
        return {
            "error": f"File not found: {file_path}",
            "action_plan": ["Verify the file path and ensure the file exists"],
        }
    if not file_path.is_file():
        return {
            "error": f"Path is not a file: {file_path}",
            "action_plan": ["Provide a path to a file, not a directory"],
        }
    try:
        file_size = file_path.stat().st_size
        if file_size > max_file_bytes:
            file_info = await create_file_audit(file_path)
            return {
                "error": (
                    f"File too large: {file_size} bytes (limit: {max_file_bytes})"
                ),
                "file_info": file_info,
                "action_plan": ["Reduce file size or increase max_file_bytes limit"],
            }
    except Exception as exc:
        return {
            "error": f"Could not access file: {exc}",
            "action_plan": ["Verify file permissions and accessibility"],
        }
    return None


def enrich_read_result(
    result: dict[str, Any],
    *,
    file_path: Path,
    extension: str,
    file_type: str,
    processing_method: str,
    processing_time: float,
    max_pdf_pages: int,
    max_file_bytes: int,
    chunk_size: int,
    ocr_enabled: bool,
    text_extensions: set[str],
    image_extensions: set[str],
    yaml_extensions: set[str],
    xml_extensions: set[str],
    docx_extensions: set[str],
) -> dict[str, Any]:
    """Attach common metadata, structure preview, and audit details."""
    result.update(
        {
            "processing_profile": {
                "duration_seconds": round(processing_time, 3),
                "file_extension": extension,
                "processing_method": processing_method,
            },
            "structure_preview": create_structure_preview(
                extension,
                result,
                text_extensions=text_extensions,
                image_extensions=image_extensions,
                yaml_extensions=yaml_extensions,
                xml_extensions=xml_extensions,
                docx_extensions=docx_extensions,
            ),
            "audit_trail": {
                "file_path": str(file_path),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "format": file_type,
                "agent_config": {
                    "max_pdf_pages": max_pdf_pages,
                    "max_file_bytes": max_file_bytes,
                    "chunk_size": chunk_size,
                    "ocr_enabled": ocr_enabled,
                },
            },
        }
    )
    return result


__all__ = ["enrich_read_result", "validate_read_target"]
