# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Resource-safety wrappers for streaming pipelines."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
import contextlib
from contextlib import AbstractContextManager
from types import TracebackType
from typing import (
    Any,
    Generic,
    TypeVar,
    cast,
)

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
            with contextlib.suppress(Exception):
                close()
        return


def with_resource_stream(gen: Iterator[R]) -> AbstractContextManager[Iterator[R]]:
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
                with contextlib.suppress(Exception):
                    close()
        return


def managed_stream(
    factory: Callable[[], Iterator[R]],
) -> AbstractContextManager[Iterator[R]]:
    """Create generator from factory inside context; guarantees cleanup."""

    return _ManagedStream(factory)


def nested_managed(
    managers: Sequence[AbstractContextManager[Any]],
) -> AbstractContextManager[tuple[Any, ...]]:
    """Compose multiple context managers; returns tuple of entered values."""

    class _Nested(AbstractContextManager[tuple[Any, ...]]):
        def __init__(self, managers: Sequence[AbstractContextManager[Any]]) -> None:
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
            if self._stack is None:  # pragma: no cover - defensive invariant
                raise RuntimeError("nested resource stack was not entered")
            self._stack.__exit__(exc_type, exc, tb)
            return

    return _Nested(managers)


def auto_close(obj: Any) -> AbstractContextManager[Any]:
    """Close obj if it has .close(); respect context protocol; otherwise no-op."""

    if hasattr(obj, "__enter__") and hasattr(obj, "__exit__"):
        return cast(AbstractContextManager[Any], obj)

    @contextlib.contextmanager
    def _cm() -> Iterator[Any]:
        try:
            yield obj
        finally:
            close = getattr(obj, "close", None)
            if callable(close):
                with contextlib.suppress(Exception):
                    close()

    return _cm()


__all__ = [
    "with_resource_stream",
    "managed_stream",
    "nested_managed",
    "auto_close",
]
