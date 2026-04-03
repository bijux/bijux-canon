# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from bijux_rag.policies.memo import lru_cache_custom, memoize_keyed


@given(inputs=st.lists(st.integers(), min_size=100, max_size=1000, unique=False))
def test_observational_purity(inputs: list[int]) -> None:
    def expensive(x: int) -> int:
        return x**3 + x**2 + x

    cached = lru_cache_custom(maxsize=None)(expensive)
    assert [cached(x) for x in inputs] == [expensive(x) for x in inputs]

    calls = 0

    def counted(x: int) -> int:
        nonlocal calls
        calls += 1
        return expensive(x)

    cached2 = lru_cache_custom(maxsize=None)(counted)
    for x in inputs:
        cached2(x)
    assert calls == len(set(inputs))


@given(inputs=st.lists(st.text(), min_size=100, max_size=500, unique=False))
def test_keyed_memo_hit_miss(inputs: list[str]) -> None:
    calls = 0

    def expensive(s: str) -> int:
        nonlocal calls
        calls += 1
        return len(s) * 17

    memo = memoize_keyed(lambda s: s, maxsize=None)(expensive)
    for s in inputs:
        memo(s)
    assert calls == len(set(inputs))
