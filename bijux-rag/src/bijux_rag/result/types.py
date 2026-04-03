# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Result/Option containers for pure, streaming-friendly error handling (end-of-Bijux RAG).

Bijux RAG extends the ADTs with:
- Canonical instance methods (`map`, `map_err`, `and_then`, `ap`) for lawful composition
- Boundary-friendly helpers (`or_else`, `tap`)
- A unified Option encoding (`Some[T] | NoneVal`) with a stable singleton `NONE`
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Generic, Mapping, NamedTuple, TypeAlias, TypeGuard, TypeVar, cast

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")
E = TypeVar("E")
F = TypeVar("F")


def curry2(f: Callable[[T, U], V]) -> Callable[[T], Callable[[U], V]]:
    return lambda x: lambda y: f(x, y)


@dataclass(frozen=True)
class Ok(Generic[T, E]):
    value: T

    def and_then(self, f: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        return f(self.value)

    def bind(self, f: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        return self.and_then(f)

    def map(self, f: Callable[[T], U]) -> "Result[U, E]":
        return Ok(f(self.value))

    def map_err(self, f: Callable[[E], F]) -> "Result[T, F]":
        _ = f
        return cast("Result[T, F]", self)

    def ap(self, arg: "Result[U, E]") -> "Result[V, E]":
        if isinstance(arg, Err):
            return arg  # type: ignore[return-value]
        func = cast(Callable[[U], V], self.value)
        return Ok(func(arg.value))

    def or_else(self, _: Callable[[E], T]) -> T:
        return self.value

    def tap(self, side: Callable[[T], None]) -> "Ok[T, E]":
        side(self.value)
        return self

    def recover(self, f: Callable[[E], T]) -> "Result[T, E]":
        _ = f
        return cast("Result[T, E]", self)

    def unwrap_or(self, default: T) -> T:
        _ = default
        return self.value

    def to_option(self) -> "Option[T]":
        return Some(self.value)


@dataclass(frozen=True)
class Err(Generic[T, E]):
    error: E

    def and_then(self, _: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        return cast("Result[U, E]", self)

    def bind(self, f: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        _ = f
        return cast("Result[U, E]", self)

    def map(self, _: Callable[[T], U]) -> "Result[U, E]":
        return cast("Result[U, E]", self)

    def map_err(self, f: Callable[[E], F]) -> "Result[T, F]":
        return Err(f(self.error))

    def ap(self, _: "Result[Any, E]") -> "Result[V, E]":
        return cast("Result[V, E]", self)

    def or_else(self, op: Callable[[E], T]) -> T:
        return op(self.error)

    def tap(self, _: Callable[[T], None]) -> "Err[T, E]":
        return self

    def recover(self, f: Callable[[E], T]) -> "Result[T, E]":
        return Ok(f(self.error))

    def unwrap_or(self, default: T) -> T:
        return default

    def to_option(self) -> "Option[T]":
        return NONE


Result: TypeAlias = Ok[T, E] | Err[T, E]


def is_ok(r: Result[T, E]) -> TypeGuard[Ok[T, E]]:
    return isinstance(r, Ok)


def is_err(r: Result[T, E]) -> TypeGuard[Err[T, E]]:
    return isinstance(r, Err)


def map_result(f: Callable[[T], U], r: Result[T, E]) -> Result[U, E]:
    return r.map(f)


def map_err(f: Callable[[E], F], r: Result[T, E]) -> Result[T, F]:
    return r.map_err(f)


def bind_result(f: Callable[[T], Result[U, E]], r: Result[T, E]) -> Result[U, E]:
    return r.bind(f)


def recover(f: Callable[[E], T], r: Result[T, E]) -> Result[T, E]:
    return r.recover(f)


def unwrap_or(r: Result[T, E], default: T) -> T:
    return r.unwrap_or(default)


def liftA2(f: Callable[[T, U], V], a: Result[T, E], b: Result[U, E]) -> Result[V, E]:
    """Lift a pure 2-arg function into Results (fail-fast applicative)."""

    return a.map(curry2(f)).ap(b)


@dataclass(frozen=True)
class Some(Generic[T]):
    value: T

    def __post_init__(self) -> None:
        if self.value is None:
            raise ValueError("Some(None) forbidden – use NoneVal() / NONE")

    def map(self, f: Callable[[T], U]) -> "Option[U]":
        return Some(f(self.value))

    def and_then(self, f: Callable[[T], "Option[U]"]) -> "Option[U]":
        return f(self.value)

    def bind(self, f: Callable[[T], "Option[U]"]) -> "Option[U]":
        return self.and_then(f)

    def unwrap_or(self, default: T) -> T:
        _ = default
        return self.value

    def unwrap_or_else(self, default: Callable[[], T]) -> T:
        _ = default
        return self.value

    def or_else(self, _: Callable[[], T]) -> T:
        return self.value

    def tap(self, side: Callable[[T], None]) -> "Some[T]":
        side(self.value)
        return self


@dataclass(frozen=True)
class NoneVal:
    def map(self, _: Callable[[Any], U]) -> "Option[U]":
        return self

    def and_then(self, _: Callable[[Any], "Option[U]"]) -> "Option[U]":
        return self

    def bind(self, f: Callable[[Any], "Option[U]"]) -> "Option[U]":
        _ = f
        return self

    def unwrap_or(self, default: T) -> T:
        return default

    def unwrap_or_else(self, default: Callable[[], T]) -> T:
        return default()

    def or_else(self, op: Callable[[], T]) -> T:
        return op()

    def tap(self, _: Callable[[Any], None]) -> "NoneVal":
        return self


NONE: NoneVal = NoneVal()
Option: TypeAlias = Some[T] | NoneVal


def to_option(r: Result[T, E]) -> Option[T]:
    return r.to_option()


def is_some(o: Option[T]) -> TypeGuard[Some[T]]:
    return isinstance(o, Some)


def is_none(o: Option[T]) -> TypeGuard[NoneVal]:
    return isinstance(o, NoneVal)


def map_option(f: Callable[[T], U], o: Option[T]) -> Option[U]:
    return o.map(f)


def bind_option(f: Callable[[T], Option[U]], o: Option[T]) -> Option[U]:
    return o.bind(f)


def unwrap_or_else(o: Option[T], default: Callable[[], T]) -> T:
    return o.unwrap_or_else(default)


def option_from_nullable(x: T | None) -> Option[T]:
    return NONE if x is None else Some(x)


def option_to_nullable(o: Option[T]) -> T | None:
    return o.value if isinstance(o, Some) else None


class ErrInfo(NamedTuple):
    """Structured error provenance for per-record failures."""

    code: str
    msg: str
    stage: str = ""
    path: tuple[int, ...] = ()
    cause: BaseException | None = None
    ctx: Mapping[str, object] | None = None

    @staticmethod
    def from_exception(
        exc: BaseException,
        *,
        code: str = "UNEXPECTED",
        msg: str | None = None,
        stage: str = "",
        path: tuple[int, ...] = (),
        ctx: Mapping[str, object] | None = None,
        meta: Mapping[str, object] | None = None,
    ) -> "ErrInfo":
        return make_errinfo(
            code=code,
            msg=msg or str(exc),
            stage=stage,
            path=path,
            exc=exc,
            ctx=ctx,
            meta=meta,
        )

    @staticmethod
    def from_exc(
        exc: BaseException,
        *,
        code: str = "UNEXPECTED",
        msg: str | None = None,
        stage: str = "",
        path: tuple[int, ...] = (),
        ctx: Mapping[str, object] | None = None,
        meta: Mapping[str, object] | None = None,
    ) -> "ErrInfo":
        return ErrInfo.from_exception(
            exc,
            code=code,
            msg=msg,
            stage=stage,
            path=path,
            ctx=ctx,
            meta=meta,
        )


def make_errinfo(
    code: str,
    msg: str,
    stage: str = "",
    path: tuple[int, ...] = (),
    cause: BaseException | None = None,
    ctx: Mapping[str, object] | None = None,
    *,
    exc: BaseException | None = None,
    meta: Mapping[str, object] | None = None,
) -> ErrInfo:
    if cause is not None and exc is not None:
        raise ValueError("Provide only one of: cause, exc")
    if ctx is not None and meta is not None:
        raise ValueError("Provide only one of: ctx, meta")
    if exc is not None:
        cause = exc
    if meta is not None:
        ctx = meta
    if ctx is not None:
        if not isinstance(ctx, Mapping):
            raise ValueError("ErrInfo.ctx must be a mapping when provided")
        if isinstance(ctx, dict):
            ctx = MappingProxyType(dict(ctx))
    return ErrInfo(code=code, msg=msg, stage=stage, path=path, cause=cause, ctx=ctx)


# Bijux RAG legacy names (kept for boundary/shell style)
def result_map(res: Result[T, E], fn: Callable[[T], U]) -> Result[U, E]:
    return map_result(fn, res)


def result_and_then(res: Result[T, E], fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
    return bind_result(fn, res)


__all__ = [
    "Result",
    "Ok",
    "Err",
    "curry2",
    "liftA2",
    "ErrInfo",
    "make_errinfo",
    "is_ok",
    "is_err",
    "map_result",
    "map_err",
    "bind_result",
    "recover",
    "unwrap_or",
    "to_option",
    "Option",
    "Some",
    "NoneVal",
    "NONE",
    "is_some",
    "is_none",
    "map_option",
    "bind_option",
    "unwrap_or_else",
    "option_from_nullable",
    "option_to_nullable",
    "result_map",
    "result_and_then",
]
