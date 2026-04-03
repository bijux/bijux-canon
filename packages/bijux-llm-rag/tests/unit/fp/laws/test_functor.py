# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from dataclasses import dataclass

from hypothesis import given
from hypothesis import strategies as st

from bijux_rag.fp.core import Err, Ok
from bijux_rag.fp.functor import (
    NONE,
    Some,
    compose,
    iter_map,
    list_map,
    option_map,
    result_map,
)


@dataclass(frozen=True)
class DummyErr:
    msg: str


@given(x=st.integers())
def test_option_identity(x: int) -> None:
    opt = Some(x)
    assert option_map(lambda v: v)(opt) == opt
    assert option_map(lambda v: v)(NONE) is NONE


@given(x=st.integers())
def test_option_composition(x: int) -> None:
    def f(v: int) -> int:
        return v + 1

    def g(v: int) -> int:
        return v * 2

    opt = Some(x)
    assert option_map(g)(option_map(f)(opt)) == option_map(compose(f, g))(opt)


@given(
    res=st.one_of(st.builds(Ok, st.integers()), st.builds(Err, st.builds(DummyErr, msg=st.text())))
)
def test_result_functor_laws(res) -> None:
    assert result_map(lambda x: x)(res) == res

    def f(x: int) -> int:
        return x + 1

    def g(x: int) -> int:
        return x * 2

    assert result_map(g)(result_map(f)(res)) == result_map(compose(f, g))(res)


@given(xs=st.lists(st.integers()))
def test_list_functor_laws(xs: list[int]) -> None:
    assert list_map(lambda x: x)(xs) == tuple(xs)

    def f(x: int) -> int:
        return x + 1

    def g(x: int) -> int:
        return x * 2

    assert list_map(g)(list_map(f)(xs)) == list_map(compose(f, g))(xs)


@given(xs=st.lists(st.integers()))
def test_iter_functor_laws(xs: list[int]) -> None:
    def f(x: int) -> int:
        return x + 1

    def g(x: int) -> int:
        return x * 2

    assert tuple(iter_map(g)(iter_map(f)(xs))) == tuple(iter_map(compose(f, g))(xs))
    assert tuple(iter_map(lambda x: x)(xs)) == tuple(xs)
