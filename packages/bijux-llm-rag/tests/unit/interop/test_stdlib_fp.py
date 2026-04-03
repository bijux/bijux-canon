# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import operator
from functools import partial, reduce
from itertools import chain

from hypothesis import given, settings
from hypothesis import strategies as st

from bijux_rag.interop.stdlib_fp import merge_streams, running_sum


@given(a=st.lists(st.integers()), b=st.lists(st.integers()))
@settings(max_examples=200)
def test_merge_streams_equiv_to_concat(a: list[int], b: list[int]) -> None:
    assert list(merge_streams(a, b)) == list(chain(a, b)) == a + b


@given(n=st.integers(min_value=-100, max_value=100), x=st.integers(min_value=-100, max_value=100))
@settings(max_examples=200)
def test_partial_equiv(n: int, x: int) -> None:
    add_n = partial(operator.add, n)
    assert add_n(x) == n + x


@given(xs=st.lists(st.integers(), min_size=1, max_size=200))
@settings(max_examples=200)
def test_reduce_add_equiv_sum(xs: list[int]) -> None:
    assert reduce(operator.add, xs) == sum(xs)


@given(xs=st.lists(st.integers(), max_size=200))
@settings(max_examples=200)
def test_running_sum_matches_manual(xs: list[int]) -> None:
    out = list(running_sum(xs))
    acc = 0
    manual: list[int] = []
    for x in xs:
        acc += x
        manual.append(acc)
    assert out == manual
