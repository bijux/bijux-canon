# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from collections.abc import Callable

import hypothesis.strategies as st
from hypothesis import given, settings

from bijux_rag.result.types import Err, NoneVal, Ok, Option, Result, Some

settings.register_profile("ci", max_examples=300, derandomize=True, deadline=None)
settings.load_profile("ci")


def st_values() -> st.SearchStrategy[int]:
    return st.integers(-20, 20)


def st_errors() -> st.SearchStrategy[str]:
    return st.text(min_size=0, max_size=8)


def st_result() -> st.SearchStrategy[Result[int, str]]:
    return st.one_of(st.builds(Ok, st_values()), st.builds(Err, st_errors()))


def st_option() -> st.SearchStrategy[Option[int]]:
    return st.one_of(st.builds(Some, st_values()), st.builds(NoneVal))


@st.composite
def st_func_to_result(draw) -> Callable[[int], Result[int, str]]:
    ok_val = draw(st_values())
    err_val = draw(st_errors())
    threshold = draw(st.integers(-10, 10))

    def f(x: int) -> Result[int, str]:
        return Ok(ok_val if x >= threshold else x * 2) if x % 2 == 0 else Err(err_val)

    return f


@st.composite
def st_func_to_option(draw) -> Callable[[int], Option[int]]:
    some_val = draw(st_values())
    threshold = draw(st.integers(-10, 10))

    def f(x: int) -> Option[int]:
        return Some(some_val if x >= threshold else x + 1) if (x % 3) != 0 else NoneVal()

    return f


@given(x=st_values(), f=st_func_to_result())
def test_result_left_identity(x: int, f: Callable[[int], Result[int, str]]) -> None:
    assert Ok(x).and_then(f) == f(x)


@given(m=st_result())
def test_result_right_identity(m: Result[int, str]) -> None:
    assert m.and_then(Ok) == m


@given(m=st_result(), f=st_func_to_result(), g=st_func_to_result())
def test_result_associativity(
    m: Result[int, str],
    f: Callable[[int], Result[int, str]],
    g: Callable[[int], Result[int, str]],
) -> None:
    assert m.and_then(f).and_then(g) == m.and_then(lambda x: f(x).and_then(g))


@given(m=st_result())
def test_result_functor_identity(m: Result[int, str]) -> None:
    assert m.map(lambda x: x) == m


@given(m=st_result(), a=st.integers(-10, 10), b=st.integers(-10, 10))
def test_result_functor_composition(m: Result[int, str], a: int, b: int) -> None:
    def f(x: int) -> int:
        return x + a

    def g(x: int) -> int:
        return x * b

    assert m.map(f).map(g) == m.map(lambda x: g(f(x)))


@given(m=st_result())
def test_result_bifunctor_identity(m: Result[int, str]) -> None:
    assert m.map_err(lambda e: e) == m


@given(m=st_result(), prefix=st.text(max_size=4), suffix=st.text(max_size=4))
def test_result_bifunctor_composition(m: Result[int, str], prefix: str, suffix: str) -> None:
    def f(e: str) -> str:
        return prefix + e

    def g(e: str) -> str:
        return e + suffix

    assert m.map_err(f).map_err(g) == m.map_err(lambda e: g(f(e)))


@given(e=st_errors())
def test_result_short_circuit(e: str) -> None:
    assert Err(e).and_then(lambda _: Ok(999)) == Err(e)


@given(m=st_result())
def test_result_tap_transparent(m: Result[int, str]) -> None:
    seen: list[int] = []
    out = m.tap(lambda v: seen.append(v))
    assert out == m
    assert seen == ([m.value] if isinstance(m, Ok) else [])


@given(x=st_values(), f=st_func_to_option())
def test_option_left_identity(x: int, f: Callable[[int], Option[int]]) -> None:
    assert Some(x).and_then(f) == f(x)


@given(o=st_option())
def test_option_right_identity(o: Option[int]) -> None:
    assert o.and_then(Some) == o


@given(o=st_option(), f=st_func_to_option(), g=st_func_to_option())
def test_option_associativity(
    o: Option[int], f: Callable[[int], Option[int]], g: Callable[[int], Option[int]]
) -> None:
    assert o.and_then(f).and_then(g) == o.and_then(lambda x: f(x).and_then(g))


@given(o=st_option())
def test_option_functor_identity(o: Option[int]) -> None:
    assert o.map(lambda x: x) == o


@given(o=st_option(), a=st.integers(-10, 10), b=st.integers(-10, 10))
def test_option_functor_composition(o: Option[int], a: int, b: int) -> None:
    def f(x: int) -> int:
        return x + a

    def g(x: int) -> int:
        return x * b

    assert o.map(f).map(g) == o.map(lambda x: g(f(x)))


def test_option_short_circuit() -> None:
    assert NoneVal().and_then(lambda _: Some(999)) == NoneVal()


@given(o=st_option())
def test_option_tap_transparent(o: Option[int]) -> None:
    seen: list[int] = []
    out = o.tap(lambda v: seen.append(v))
    assert out == o
    assert seen == ([o.value] if isinstance(o, Some) else [])
