# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Laws and smoke tests for the functional helpers used by the pipeline."""

from __future__ import annotations

import hypothesis.strategies as st
from hypothesis import given

from bijux_rag import ffilter, flatmap, fmap, identity, pipe


@given(xs=st.lists(st.integers()))
def test_fmap_identity_law(xs: list[int]) -> None:
    assert list(fmap(identity)(xs)) == xs


@given(xs=st.lists(st.integers()))
def test_fmap_composition_law(xs: list[int]) -> None:
    def inc(x: int) -> int:
        return x + 1

    def double(x: int) -> int:
        return x * 2

    left = list(fmap(lambda x: double(inc(x)))(xs))
    right = list(fmap(double)(fmap(inc)(xs)))
    assert left == right


@given(xs=st.lists(st.integers()))
def test_pipe_matches_manual_threading(xs: list[int]) -> None:
    def drop_first(items: list[int]) -> list[int]:
        return items[1:]

    def keep_even(items: list[int]) -> list[int]:
        return [x for x in items if x % 2 == 0]

    assert pipe(xs, drop_first, keep_even) == keep_even(drop_first(xs))


def test_ffilter_and_flatmap_are_lazy_iterators() -> None:
    calls: list[int] = []

    def pred(x: int) -> bool:
        calls.append(x)
        return x % 2 == 0

    it = iter([1, 2, 3, 4])
    out = ffilter(pred)(it)
    assert next(out) == 2
    assert calls == [1, 2]

    def expand(x: int) -> list[int]:
        return [x, x]

    out2 = flatmap(expand)([1, 2])
    assert list(out2) == [1, 1, 2, 2]
