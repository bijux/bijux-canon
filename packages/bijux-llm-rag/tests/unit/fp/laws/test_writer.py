# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import hypothesis.strategies as st
from hypothesis import given, settings

from bijux_rag.fp.effects.writer import Writer, listen, pure, run_writer, tell

settings.register_profile("ci", max_examples=250, derandomize=True, deadline=None)
settings.load_profile("ci")


@given(x=st.integers(-20, 20))
def test_writer_left_identity(x: int) -> None:
    def f(n: int) -> Writer[int, str]:
        return Writer(lambda: (n + 1, ("inc",)))

    assert run_writer(pure(x).and_then(f)) == run_writer(f(x))


@given(entries=st.lists(st.text(max_size=10)))
def test_writer_right_identity(entries: list[str]) -> None:
    w = Writer(lambda: (42, tuple(entries)))
    assert run_writer(w.and_then(pure)) == run_writer(w)


@given(entries=st.lists(st.text(max_size=10)))
def test_writer_associativity(entries: list[str]) -> None:
    w = Writer(lambda: (42, tuple(entries)))

    def f(a: int) -> Writer[int, str]:
        return Writer(lambda: (a + 1, ("f",)))

    def g(b: int) -> Writer[int, str]:
        return Writer(lambda: (b * 2, ("g",)))

    assert run_writer(w.and_then(f).and_then(g)) == run_writer(
        w.and_then(lambda x: f(x).and_then(g))
    )


@given(e1=st.text(max_size=20), e2=st.text(max_size=20))
def test_writer_tell_append(e1: str, e2: str) -> None:
    assert run_writer(tell(e1).and_then(lambda _: tell(e2))) == (None, (e1, e2))


@given(entries=st.lists(st.text(max_size=20)))
def test_writer_listen_roundtrip(entries: list[str]) -> None:
    w = Writer(lambda: (42, tuple(entries)))
    assert run_writer(listen(w).map(lambda pair: pair[0])) == run_writer(w)
