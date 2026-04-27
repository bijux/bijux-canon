"""Bijux Agent package entry point."""

from __future__ import annotations

from typing import Any

__all__ = [
    "API_VERSION",
]


def __getattr__(name: str) -> Any:
    """Resolve optional package-root exports lazily."""
    if name == "API_VERSION":
        from bijux_canon_agent.api.v1 import API_VERSION

        return API_VERSION
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
