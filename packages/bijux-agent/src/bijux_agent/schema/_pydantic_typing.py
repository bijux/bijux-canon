"""Lightweight typing helpers that mirror the Pydantic surface for the core schema."""

from __future__ import annotations

from typing import Any, Protocol


class ConfigDict(Protocol):
    """Minimal configuration dictionary used by typed models during type checks."""

    def __init__(self, **kwargs: Any) -> None: ...


class BaseModel:  # pragma: no cover (type-only helper)
    """Typed stand-in for the real Pydantic BaseModel while type checking."""

    model_config: ConfigDict

    def __init__(self, **data: Any) -> None:
        return None

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {}

    def dict(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {}
