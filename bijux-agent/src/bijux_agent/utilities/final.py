"""Runtime helper to enforce final class semantics."""

from __future__ import annotations

from typing import Any, TypeVar

T = TypeVar("T", bound=type[Any])


def final_class(cls: T) -> T:
    """Mark the class as final so subclassing raises at runtime."""

    def __init_subclass__(subcls: type[Any], **kwargs: Any) -> None:  # noqa: N807
        raise TypeError(f"{cls.__name__} is final and cannot be subclassed")

    cls.__init_subclass__ = classmethod(__init_subclass__)
    return cls
