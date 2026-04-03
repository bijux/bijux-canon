"""Typed stub for Pydantic's ConfigDict builder to satisfy mypy."""

from __future__ import annotations

from typing import Any, Iterator, MutableMapping


class ConfigDict(MutableMapping[str, Any]):
    def __init__(
        self,
        *,
        frozen: bool | None = None,
        allow_mutation: bool | None = None,
        extra: str | None = None,
        arbitrary_types_allowed: bool | None = None,
        **kwargs: Any,
    ) -> None: ...

    def __getitem__(self, key: str) -> Any: ...

    def __setitem__(self, key: str, value: Any) -> None: ...

    def __delitem__(self, key: str) -> None: ...

    def __iter__(self) -> Iterator[str]: ...

    def __len__(self) -> int: ...
