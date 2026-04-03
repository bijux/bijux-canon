# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Resource-safety wrappers for streaming pipelines (end-of-Bijux RAG)."""

from __future__ import annotations

import contextlib
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Any, Callable, ContextManager, Generic, Iterator, Sequence, TypeVar, cast

R = TypeVar("R")


class _ResourceStream(Generic[R], AbstractContextManager[Iterator[R]]):
    def __init__(self, gen: Iterator[R]) -> None:
        self._gen = gen

    def __enter__(self) -> Iterator[R]:
        return self._gen

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        del exc_type, exc, tb
        close = getattr(self._gen, "close", None)
        if callable(close):
            try:
                close()
            except Exception:  # noqa: BLE001 - never mask the original exception
                pass
        return None


def with_resource_stream(gen: Iterator[R]) -> ContextManager[Iterator[R]]:
    """Wrap an existing generator; guarantees .close() on all exit paths."""

    return _ResourceStream(gen)


class _ManagedStream(Generic[R], AbstractContextManager[Iterator[R]]):
    def __init__(self, factory: Callable[[], Iterator[R]]) -> None:
        self._factory = factory
        self._gen: Iterator[R] | None = None

    def __enter__(self) -> Iterator[R]:
        self._gen = self._factory()
        return self._gen

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        del exc_type, exc, tb
        if self._gen is not None:
            close = getattr(self._gen, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:  # noqa: BLE001 - never mask the original exception
                    pass
        return None


def managed_stream(factory: Callable[[], Iterator[R]]) -> ContextManager[Iterator[R]]:
    """Create generator from factory inside context; guarantees cleanup."""

    return _ManagedStream(factory)


def nested_managed(managers: Sequence[ContextManager[Any]]) -> ContextManager[tuple[Any, ...]]:
    """Compose multiple context managers; returns tuple of entered values."""

    class _Nested(AbstractContextManager[tuple[Any, ...]]):
        def __init__(self, managers: Sequence[ContextManager[Any]]) -> None:
            self._managers = managers
            self._stack: contextlib.ExitStack | None = None

        def __enter__(self) -> tuple[Any, ...]:
            self._stack = contextlib.ExitStack()
            return tuple(self._stack.enter_context(m) for m in self._managers)

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            assert self._stack is not None
            self._stack.__exit__(exc_type, exc, tb)
            return None

    return _Nested(managers)


def auto_close(obj: Any) -> ContextManager[Any]:
    """Close obj if it has .close(); respect context protocol; otherwise no-op."""

    if hasattr(obj, "__enter__") and hasattr(obj, "__exit__"):
        return cast(ContextManager[Any], obj)

    @contextlib.contextmanager
    def _cm() -> Iterator[Any]:
        try:
            yield obj
        finally:
            close = getattr(obj, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:  # noqa: BLE001
                    pass

    return _cm()


__all__ = [
    "with_resource_stream",
    "managed_stream",
    "nested_managed",
    "auto_close",
]
