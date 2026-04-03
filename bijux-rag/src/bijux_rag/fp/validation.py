# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG Validation: applicative checks that accumulate all errors (end-of-Bijux RAG)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol, Tuple, TypeVar, cast

from .core import Err, Ok, Result, Validation, VFailure, VSuccess

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")
W = TypeVar("W")
E = TypeVar("E")
A = TypeVar("A")
A1 = TypeVar("A1")
B1 = TypeVar("B1")
C1 = TypeVar("C1")


def compose(f: Callable[[B1], C1]) -> Callable[[Callable[[A1], B1]], Callable[[A1], C1]]:
    """Curried function composition for applicative laws.

    In the applicative composition law we need:
      pure(compose) <*> u <*> v <*> w
    so `compose` must be curried.
    """

    def _g(g: Callable[[A1], B1]) -> Callable[[A1], C1]:
        def _x(x: A1) -> C1:
            return f(g(x))

        return _x

    return _g


class CombineErrors(Protocol[E]):
    def __call__(self, left: Tuple[E, ...], right: Tuple[E, ...]) -> Tuple[E, ...]: ...


def v_pure(x: T) -> Validation[T, E]:
    return VSuccess(value=x)


v_success = v_pure


def v_failure(errors: Sequence[E]) -> VFailure[E]:
    t = tuple(errors)
    if not t:
        raise ValueError("VFailure must contain at least one error")
    return VFailure(errors=t)


def v_map(f: Callable[[T], U]) -> Callable[[Validation[T, E]], Validation[U, E]]:
    def _inner(v: Validation[T, E]) -> Validation[U, E]:
        if isinstance(v, VSuccess):
            return VSuccess(value=f(v.value))
        return cast(Validation[U, E], v)

    return _inner


def v_ap(
    vf: Validation[Callable[[T], U], E],
    vx: Validation[T, E],
    *,
    combine: CombineErrors[E] = lambda a, b: a + b,
) -> Validation[U, E]:
    if isinstance(vf, VSuccess) and isinstance(vx, VSuccess):
        return v_success(vf.value(vx.value))

    left_errs = vf.errors if isinstance(vf, VFailure) else ()
    right_errs = vx.errors if isinstance(vx, VFailure) else ()
    combined = combine(left_errs, right_errs)
    if not combined:
        raise ValueError("combine must not return empty tuple (must treat () as identity)")
    return v_failure(combined)


def v_liftA2(
    f: Callable[[T, U], V],
    a: Validation[T, E],
    b: Validation[U, E],
    *,
    combine: CombineErrors[E] = lambda a, b: a + b,
) -> Validation[V, E]:
    def curried(x: T) -> Callable[[U], V]:
        def _y(y: U) -> V:
            return f(x, y)

        return _y

    return v_ap(v_map(curried)(a), b, combine=combine)


def v_liftA3(
    f: Callable[[T, U, V], W],
    a: Validation[T, E],
    b: Validation[U, E],
    c: Validation[V, E],
    *,
    combine: CombineErrors[E] = lambda a, b: a + b,
) -> Validation[W, E]:
    def curried(x: T) -> Callable[[U], Callable[[V], W]]:
        def _y(y: U) -> Callable[[V], W]:
            def _z(z: V) -> W:
                return f(x, y, z)

            return _z

        return _y

    step1 = v_map(curried)(a)
    step2 = v_ap(step1, b, combine=combine)
    return v_ap(step2, c, combine=combine)


def v_sequence(
    vs: Sequence[Validation[T, E]],
    *,
    combine: CombineErrors[E] = lambda a, b: a + b,
) -> Validation[tuple[T, ...], E]:
    acc: Validation[tuple[T, ...], E] = v_success(())
    for v in vs:
        acc = v_liftA2(lambda xs, x: xs + (x,), acc, v, combine=combine)
    return acc


def v_traverse(
    items: Sequence[A],
    f: Callable[[A], Validation[T, E]],
    *,
    combine: CombineErrors[E] = lambda a, b: a + b,
) -> Validation[tuple[T, ...], E]:
    return v_sequence([f(x) for x in items], combine=combine)


def to_validation(res: Result[T, E]) -> Validation[T, E]:
    return v_success(res.value) if isinstance(res, Ok) else v_failure((res.error,))


def from_validation(v: Validation[T, E]) -> Result[T, tuple[E, ...]]:
    return Ok(v.value) if isinstance(v, VSuccess) else Err(v.errors)


def dedup_stable(left: tuple[E, ...], right: tuple[E, ...]) -> tuple[E, ...]:
    seen: set[E] = set()
    out: list[E] = []
    for e in left + right:
        if e not in seen:
            seen.add(e)
            out.append(e)
    return tuple(out)


__all__ = [
    "Validation",
    "VSuccess",
    "VFailure",
    "v_pure",
    "v_success",
    "v_failure",
    "v_map",
    "v_ap",
    "v_liftA2",
    "v_liftA3",
    "v_sequence",
    "v_traverse",
    "to_validation",
    "from_validation",
    "dedup_stable",
    "compose",
]
