"""Pydantic stub used during mypy runs to document BaseModel APIs."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Sequence

from .config import ConfigDict


class BaseModel:
    model_config: ConfigDict

    def __init__(self, **values: Any) -> None: ...

    def model_dump(
        self,
        *,
        include: Iterable[str] | None = None,
        exclude: Iterable[str] | None = None,
        exclude_none: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        by_alias: bool = False,
    ) -> Dict[str, Any]: ...

    def dict(
        self,
        *,
        include: Iterable[str] | None = None,
        exclude: Iterable[str] | None = None,
        exclude_none: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        by_alias: bool = False,
    ) -> Dict[str, Any]: ...

    def model_dump_json(self, *, indent: int | None = None) -> str: ...

    def json(self, *, indent: int | None = None) -> str: ...


Field: Any
__all__ = ["BaseModel", "ConfigDict", "Field"]
