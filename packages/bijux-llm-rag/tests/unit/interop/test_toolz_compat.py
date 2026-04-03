# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from bijux_rag.interop.toolz_compat import compose, curried_filter, curried_map, pipe, reduceby


@given(xs=st.lists(st.integers(), max_size=200))
@settings(max_examples=200)
def test_pipe_left_to_right(xs: list[int]) -> None:
    out = pipe(xs, curried_map(lambda x: x + 1), list)
    assert out == [x + 1 for x in xs]


@given(x=st.integers())
@settings(max_examples=200)
def test_compose_right_to_left(x: int) -> None:
    f = compose(lambda y: y * 2, lambda y: y + 1)
    assert f(x) == (x + 1) * 2


@given(xs=st.lists(st.integers(), max_size=200))
@settings(max_examples=200)
def test_curried_filter(xs: list[int]) -> None:
    keep_even = curried_filter(lambda x: x % 2 == 0)
    assert list(keep_even(xs)) == [x for x in xs if x % 2 == 0]


@given(xs=st.lists(st.text(min_size=0), max_size=200))
@settings(max_examples=200)
def test_reduceby_counts_by_first_char(xs: list[str]) -> None:
    def key(s: str) -> str:
        return s[:1]

    def bump(acc: int, _s: str) -> int:
        return acc + 1

    got = reduceby(key, bump, xs, 0)
    expected: dict[str, int] = {}
    for s in xs:
        k = s[:1]
        expected[k] = expected.get(k, 0) + 1
    assert got == expected
