# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from bijux_rag.fp.monoid import LIST_STR, METRICS, SUM_INT, Metrics, Sum, tree_reduce


@given(a=st.integers(), b=st.integers(), c=st.integers())
def test_sum_int_laws(a: int, b: int, c: int) -> None:
    m = SUM_INT
    assert m.combine(m.combine(Sum(a), Sum(b)), Sum(c)) == m.combine(
        Sum(a), m.combine(Sum(b), Sum(c))
    )
    e = m.empty()
    assert m.combine(e, Sum(a)) == Sum(a)
    assert m.combine(Sum(a), e) == Sum(a)


@given(xs=st.lists(st.integers()))
def test_tree_reduce_equals_sum(xs: list[int]) -> None:
    sums = [Sum(x) for x in xs]
    assert tree_reduce(SUM_INT, sums).value == sum(xs)


@given(a=st.lists(st.text()), b=st.lists(st.text()), c=st.lists(st.text()))
def test_list_str_laws(a: list[str], b: list[str], c: list[str]) -> None:
    m = LIST_STR
    assert m.combine(m.combine(a, b), c) == m.combine(a, m.combine(b, c))
    e = m.empty()
    assert m.combine(e, a) == a
    assert m.combine(a, e) == a


_small_exact_ms = st.integers(min_value=0, max_value=10_000).map(float)
metrics_strategy = st.builds(
    Metrics,
    processed=st.integers(min_value=0, max_value=10**9),
    succeeded=st.integers(min_value=0, max_value=10**9),
    latency_sum_ms=_small_exact_ms,
    latency_max_ms=_small_exact_ms,
)


@given(a=metrics_strategy, b=metrics_strategy, c=metrics_strategy)
def test_metrics_monoid_laws(a: Metrics, b: Metrics, c: Metrics) -> None:
    m = METRICS
    assert m.combine(m.combine(a, b), c) == m.combine(a, m.combine(b, c))
    e = m.empty()
    assert m.combine(e, a) == a
    assert m.combine(a, e) == a


def test_metrics_finite_guard() -> None:
    with pytest.raises(ValueError):
        METRICS.combine(Metrics(latency_sum_ms=float("nan")), Metrics())
