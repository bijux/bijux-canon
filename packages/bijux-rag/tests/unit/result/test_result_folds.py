# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from bijux_rag.result import (
    Err,
    Ok,
    all_ok_fail_fast,
    fold_results_collect_errs,
    fold_results_collect_errs_capped,
    fold_results_fail_fast,
    fold_until_error_rate,
)


@st.composite
def result_list(draw):
    xs = draw(st.lists(st.integers(), max_size=200))
    errs = draw(st.sets(st.integers(min_value=0, max_value=max(0, len(xs) - 1))))
    out = []
    for i, x in enumerate(xs):
        out.append(Err(f"E{i}") if i in errs else Ok(x))
    return out


@given(xs=result_list())
def test_fold_fail_fast_short_circuit(xs) -> None:
    calls = 0

    def add(acc: int, x: int) -> int:
        nonlocal calls
        calls += 1
        return acc + x

    res = fold_results_fail_fast(xs, 0, add)
    if any(isinstance(r, Err) for r in xs):
        first_err = next(i for i, r in enumerate(xs) if isinstance(r, Err))
        assert calls == sum(1 for r in xs[:first_err] if isinstance(r, Ok))
        assert isinstance(res, Err)
    else:
        assert isinstance(res, Ok)


@given(xs=result_list())
def test_fold_collect_errs_equivalence(xs) -> None:
    def add(acc: int, x: int) -> int:
        return acc + x

    res = fold_results_collect_errs(xs, 0, add)
    errs = [r.error for r in xs if isinstance(r, Err)]
    if errs:
        assert isinstance(res, Err)
        assert res.error == errs
    else:
        assert isinstance(res, Ok)


@given(xs=result_list(), max_errs=st.integers(min_value=0, max_value=20))
def test_fold_collect_errs_capped(xs, max_errs: int) -> None:
    def add(acc: int, x: int) -> int:
        return acc + x

    res = fold_results_collect_errs_capped(xs, 0, add, max_errs=max_errs)
    errs = [r.error for r in xs if isinstance(r, Err)]
    capped = len(errs) > max_errs
    if errs or capped:
        assert isinstance(res, Err)
        got_errs, got_capped = res.error
        assert got_errs == errs[:max_errs]
        assert got_capped == capped
    else:
        assert isinstance(res, Ok)


def test_fold_until_error_rate_trips() -> None:
    xs = [Err("E")] * 200

    def add(acc: int, x: int) -> int:
        return acc + x

    res = fold_until_error_rate(xs, 0, add, max_rate=0.2, min_samples=10)
    assert isinstance(res, Err)


@given(xs=result_list())
def test_all_ok_fail_fast(xs) -> None:
    res = all_ok_fail_fast(xs)
    if any(isinstance(r, Err) for r in xs):
        assert isinstance(res, Err)
    else:
        assert isinstance(res, Ok)


def test_fail_fast_demand_bound() -> None:
    calls = 0

    def src():
        nonlocal calls
        for i in range(10_000):
            calls += 1
            if i == 10:
                yield Err("boom")
            else:
                yield Ok(i)

    res = fold_results_fail_fast(src(), 0, lambda a, x: a + x)
    assert isinstance(res, Err)
    assert calls == 11
