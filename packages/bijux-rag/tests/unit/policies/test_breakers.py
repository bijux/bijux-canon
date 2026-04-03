# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from bijux_rag.policies.breakers import (
    BreakInfo,
    circuit_breaker_count_emit,
    short_circuit_on_err_emit,
    short_circuit_on_err_truncate,
)
from bijux_rag.result import Err, Ok, map_result_iter


@st.composite
def int_list_with_zero(draw) -> list[int]:
    items = draw(st.lists(st.integers()))
    idx = draw(st.integers(min_value=0, max_value=len(items)))
    return [*items[:idx], 0, *items[idx:]]


@given(items=int_list_with_zero())
def test_emit_breakers_short_circuit(items: list[int]) -> None:
    first_err_pos = items.index(0)

    def f(x: int):
        return Ok(x) if x != 0 else Err("ZERO")

    results = list(short_circuit_on_err_emit(map_result_iter(f, items)))
    assert len(results) == first_err_pos + 2
    assert isinstance(results[-1], Err) and isinstance(results[-1].error, BreakInfo)
    bi = results[-1].error
    assert bi.n_ok == first_err_pos
    assert bi.n_err == 1
    assert bi.total == bi.n_ok + bi.n_err
    assert bi.last_error == "ZERO"


@given(items=st.lists(st.integers()))
def test_truncate_breakers_stop_silently(items: list[int]) -> None:
    def f(x: int):
        return Ok(x) if x != 0 else Err("ZERO")

    results = list(short_circuit_on_err_truncate(map_result_iter(f, items)))
    if 0 in items:
        assert len(results) == items.index(0) + 1
    else:
        assert len(results) == len(items)


@given(items=st.lists(st.integers()))
def test_upstream_closed_on_break(items: list[int]) -> None:
    closed = False
    sentinel_seen = False

    def src():
        nonlocal closed, sentinel_seen
        try:
            for x in items:
                yield Ok(x) if x != 0 else Err("ZERO")
                if x == 0:
                    yield Ok("should not be reached")
                    sentinel_seen = True
        finally:
            closed = True

    list(short_circuit_on_err_truncate(src()))
    assert not sentinel_seen
    assert closed


def test_count_breaker_trips_after_limit() -> None:
    xs: list = [Err("E"), Err("E"), Err("E")]
    results = list(circuit_breaker_count_emit(xs, max_errs=1))
    assert len(results) == 3
    assert isinstance(results[0], Err)
    assert isinstance(results[2], Err) and isinstance(results[2].error, BreakInfo)
    bi = results[2].error
    assert bi.n_err == 2
    assert bi.threshold["max_errs"] == 1
