# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import hypothesis.strategies as st
from hypothesis import given, settings

from bijux_rag.domain.effects.io_plan import IOPlan, io_bind, io_delay, io_pure, perform
from bijux_rag.result.types import Err, ErrInfo, Ok, Result

settings.register_profile("ci", max_examples=200, derandomize=True, deadline=None)
settings.load_profile("ci")


def st_errinfo() -> st.SearchStrategy[ErrInfo]:
    return st.builds(ErrInfo, code=st.text(max_size=8), msg=st.text(max_size=12))


@given(v=st.integers(-20, 20))
def test_io_monad_right_identity(v: int) -> None:
    plan = io_pure(v)
    assert perform(io_bind(plan, io_pure)) == perform(plan)


@given(v=st.integers(-20, 20), k=st.integers(-10, 10), m=st.integers(-10, 10))
def test_io_monad_associativity(v: int, k: int, m: int) -> None:
    def f(x: int) -> IOPlan[int]:
        return io_pure(x + k)

    def g(x: int) -> IOPlan[int]:
        return io_pure(x * m)

    left = perform(io_bind(io_bind(io_pure(v), f), g))
    right = perform(io_bind(io_pure(v), lambda x: io_bind(f(x), g)))
    assert left == right


@given(err=st_errinfo())
def test_io_bind_propagates_outer_err(err: ErrInfo) -> None:
    bad: IOPlan[int] = io_delay(lambda: Err(err))

    def f(_: int) -> IOPlan[int]:
        return io_pure(999)

    assert perform(io_bind(bad, f)) == Err(err)


def test_io_delay_is_lazy() -> None:
    calls: list[int] = []

    def thunk() -> Result[int, ErrInfo]:
        calls.append(1)
        return Ok(7)

    plan = io_delay(thunk)
    assert calls == []
    assert perform(plan) == Ok(7)
    assert calls == [1]
