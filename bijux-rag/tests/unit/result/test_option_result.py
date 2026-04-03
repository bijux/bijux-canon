# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from bijux_rag.result import NONE, Err, NoneVal, Ok, Some


@given(x=st.integers())
def test_result_functor_laws(x: int) -> None:
    r = Ok(x)
    assert r.map(lambda v: v) == r

    def f(v: int) -> int:
        return v + 1

    def g(v: int) -> int:
        return v * 2

    assert r.map(lambda v: f(g(v))) == r.map(g).map(f)


@given(x=st.integers())
def test_result_monad_laws(x: int) -> None:
    unit = Ok

    def f(v: int) -> Ok[int, object]:
        return Ok(v + 1)

    def g(v: int) -> Ok[int, object]:
        return Ok(v * 2)

    assert unit(x).bind(f) == f(x)
    r = unit(x)
    assert r.bind(unit) == r
    assert r.bind(f).bind(g) == r.bind(lambda v: f(v).bind(g))


@given(x=st.integers())
def test_option_functor_and_monad_laws(x: int) -> None:
    o = Some(x)
    assert o.map(lambda v: v) == o

    def f(v: int) -> int:
        return v + 1

    def g(v: int) -> int:
        return v * 2

    assert o.map(lambda v: f(g(v))) == o.map(g).map(f)

    unit = Some

    def mf(v: int) -> Some[int]:
        return Some(v + 1)

    def mg(v: int) -> Some[int]:
        return Some(v * 2)

    assert unit(x).bind(mf) == mf(x)
    assert o.bind(unit) == o
    assert o.bind(mf).bind(mg) == o.bind(lambda v: mf(v).bind(mg))


def test_some_none_forbidden() -> None:
    with pytest.raises(ValueError):
        Some(None)  # type: ignore[arg-type]


def test_to_option_on_err() -> None:
    assert Err("x").to_option() == NONE
    assert isinstance(Err("x").to_option(), NoneVal)
