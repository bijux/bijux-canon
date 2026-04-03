# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from itertools import islice

from hypothesis import given
from hypothesis import strategies as st

from bijux_rag.result import Err, Ok, par_try_map_iter, try_map_iter


@given(items=st.lists(st.integers()))
def test_continuation_full_output(items: list[int]) -> None:
    def f(x: int) -> int:
        if x == -1:
            raise ValueError("boom")
        return x

    results = list(try_map_iter(f, items, stage="test"))
    assert len(results) == len(items)


@given(items=st.lists(st.integers()))
def test_ordering_preservation(items: list[int]) -> None:
    tagged = list(enumerate(items))

    def f(iv: tuple[int, int]) -> tuple[int, int]:
        i, v = iv
        if v % 2 == 0:
            raise ValueError("even")
        return iv

    results = list(try_map_iter(f, tagged, stage="test", key_path=lambda iv: (iv[0],)))
    indices: list[int] = []
    for r in results:
        if isinstance(r, Ok):
            indices.append(r.value[0])
        else:
            indices.append(r.error.path[0])
    assert indices == list(range(len(items)))


def test_bounded_work_on_prefix() -> None:
    calls = 0

    def f(x: int) -> int:
        nonlocal calls
        calls += 1
        return x

    xs = range(10_000)
    out = list(islice(try_map_iter(f, xs, stage="test"), 123))
    assert len(out) == 123
    assert calls == 123


@given(items=st.lists(st.integers(), max_size=200))
def test_par_try_map_iter_preserves_length_and_order(items: list[int]) -> None:
    def f(x: int) -> int:
        if x == 0:
            raise ValueError("zero")
        return x + 1

    serial = list(try_map_iter(f, items, stage="test", key_path=lambda x: (x,)))
    par = list(
        par_try_map_iter(
            f, items, stage="test", key_path=lambda x: (x,), max_workers=4, max_in_flight=8
        )
    )
    assert len(serial) == len(par) == len(items)
    assert [isinstance(r, Err) for r in serial] == [isinstance(r, Err) for r in par]
