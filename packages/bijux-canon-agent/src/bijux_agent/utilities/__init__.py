"""Utilities package for Bijux Agent.

This package provides utility classes and functions for logging, LLM interactions,
and other helper functionalities used across the Bijux Agent project.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .logger_manager import LoggerManager, LoggerSettings

if TYPE_CHECKING:
    from .llm_utils import LLMResponse, LLMUtils

__all__ = [
    "LLMResponse",
    "LLMUtils",
    "LoggerManager",
    "LoggerSettings",
]


def __getattr__(name: str) -> Any:
    """Load LLM utilities lazily so logger imports stay lightweight."""
    if name in {"LLMResponse", "LLMUtils"}:
        from .llm_utils import LLMResponse, LLMUtils

        exports = {
            "LLMResponse": LLMResponse,
            "LLMUtils": LLMUtils,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
