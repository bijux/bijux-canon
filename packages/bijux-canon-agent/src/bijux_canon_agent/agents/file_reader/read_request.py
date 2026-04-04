"""Request-shaping helpers for file-reader execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bijux_canon_agent.observability.logging import CustomLogger, LoggerManager

from .runtime_flow import resolve_file_path


@dataclass(frozen=True)
class FileReadRequest:
    """Normalized inputs needed to run a file-read operation."""

    file_path: str
    file_suffix: str
    cache_key: str


def build_file_read_request(
    *,
    context: dict[str, Any],
    cache_key: str,
    logger: CustomLogger,
    logger_manager: LoggerManager,
) -> FileReadRequest | None:
    """Build a normalized file-read request from the incoming context."""
    file_path = resolve_file_path(
        context,
        logger=logger,
        logger_manager=logger_manager,
    )
    if file_path is None:
        return None
    return FileReadRequest(
        file_path=file_path,
        file_suffix=Path(file_path).suffix.lstrip(".").lower(),
        cache_key=cache_key,
    )


__all__ = ["FileReadRequest", "build_file_read_request"]
