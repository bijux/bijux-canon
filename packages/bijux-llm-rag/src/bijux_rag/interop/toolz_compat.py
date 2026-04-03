# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG Core 2: optional `toolz` interop with stdlib fallbacks (end-of-Bijux RAG).

We avoid importing third-party libraries at import time to keep `mypy --strict`
and installation requirements minimal. When toolz is not available, functions
fall back to simple stdlib equivalents.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Iterable, Iterator
from itertools import islice
from typing import Any, TypeVar, cast

T = TypeVar("T")
U = TypeVar("U")
K = TypeVar("K")
V = TypeVar("V")


def _try_import_toolz() -> Any | None:
    try:
        return importlib.import_module("toolz")
    except Exception:
        return None


_TOOLZ = _try_import_toolz()
TOOLZ_AVAILABLE: bool = _TOOLZ is not None


def pipe(value: T, *funcs: Callable[[Any], Any]) -> Any:
    """Apply functions left-to-right (toolz.pipe style)."""

    if TOOLZ_AVAILABLE:
        return cast(Any, _TOOLZ).pipe(value, *funcs)
    out: Any = value
    for f in funcs:
        out = f(out)
    return out


def compose(*funcs: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Compose functions right-to-left (toolz.compose style)."""

    if TOOLZ_AVAILABLE:
        return cast(Callable[[Any], Any], cast(Any, _TOOLZ).compose(*funcs))

    def _composed(x: Any) -> Any:
        out: Any = x
        for f in reversed(funcs):
            out = f(out)
        return out

    return _composed


def curried_map(f: Callable[[T], U]) -> Callable[[Iterable[T]], Iterator[U]]:
    """Return a transformer: iterable -> iterator (toolz.curried.map style)."""

    def _run(xs: Iterable[T]) -> Iterator[U]:
        return map(f, xs)

    return _run


def curried_filter(pred: Callable[[T], bool]) -> Callable[[Iterable[T]], Iterator[T]]:
    def _run(xs: Iterable[T]) -> Iterator[T]:
        return filter(pred, xs)

    return _run


def partition_all(n: int, xs: Iterable[T]) -> Iterator[list[T]]:
    """Yield lists of size up to n (toolz.itertoolz.partition_all style)."""

    if n < 1:
        raise ValueError("n must be >= 1")
    it = iter(xs)
    while True:
        batch = list(islice(it, n))
        if not batch:
            return
        yield batch


def reduceby(
    key: Callable[[T], K],
    binop: Callable[[V, T], V],
    seq: Iterable[T],
    init: V,
) -> dict[K, V]:
    """Group + reduce into a dict (toolz.reduceby semantics; materializes keys)."""

    out: dict[K, V] = {}
    for x in seq:
        k = key(x)
        if k in out:
            out[k] = binop(out[k], x)
        else:
            out[k] = binop(init, x)
    return out


__all__ = [
    "TOOLZ_AVAILABLE",
    "pipe",
    "compose",
    "curried_map",
    "curried_filter",
    "partition_all",
    "reduceby",
]
