# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from collections.abc import Callable

import hypothesis.strategies as st
from hypothesis import given, settings

from bijux_rag.fp.effects.state import State, get, modify, pure, put, run_state

settings.register_profile("ci", max_examples=250, derandomize=True, deadline=None)
settings.load_profile("ci")


@st.composite
def st_state(draw) -> State[int, int]:
    a = draw(st.integers(-5, 5))
    b = draw(st.integers(-5, 5))
    c = draw(st.integers(-5, 5))

    def run(s: int) -> tuple[int, int]:
        return a * s + b, s + c

    return State(run)


@st.composite
def st_func_to_state(draw) -> Callable[[int], State[int, int]]:
    a = draw(st.integers(-5, 5))
    b = draw(st.integers(-5, 5))

    def f(x: int) -> State[int, int]:
        return State(lambda s: (x + a, s + b))

    return f


@given(x=st.integers(-20, 20), f=st_func_to_state(), s0=st.integers(-20, 20))
def test_state_left_identity(x: int, f: Callable[[int], State[int, int]], s0: int) -> None:
    assert run_state(pure(x).and_then(f), s0) == run_state(f(x), s0)


@given(p=st_state(), s0=st.integers(-20, 20))
def test_state_right_identity(p: State[int, int], s0: int) -> None:
    assert run_state(p.and_then(pure), s0) == run_state(p, s0)


@given(p=st_state(), f=st_func_to_state(), g=st_func_to_state(), s0=st.integers(-20, 20))
def test_state_associativity(
    p: State[int, int],
    f: Callable[[int], State[int, int]],
    g: Callable[[int], State[int, int]],
    s0: int,
) -> None:
    left = run_state(p.and_then(f).and_then(g), s0)
    right = run_state(p.and_then(lambda x: f(x).and_then(g)), s0)
    assert left == right


@given(s=st.integers(-100, 100))
def test_get_put_retrieval(s: int) -> None:
    prog = get().and_then(put)
    assert run_state(prog, s) == (None, s)


@given(s_val=st.integers(-100, 100), s0=st.integers(-100, 100))
def test_put_get(s_val: int, s0: int) -> None:
    prog1 = put(s_val).and_then(lambda _: get())
    prog2 = put(s_val).map(lambda _: s_val)
    assert run_state(prog1, s0) == run_state(prog2, s0)


@given(s0=st.integers(-100, 100))
def test_modify_identity(s0: int) -> None:
    prog = modify(lambda s: s)
    assert run_state(prog, s0) == run_state(pure(None), s0)
