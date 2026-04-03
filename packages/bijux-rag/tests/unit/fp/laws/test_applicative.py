# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from typing import Callable, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from bijux_rag.fp.applicative import (
    Validation,
    VFailure,
    compose,
    dedup_stable,
    v_ap,
    v_failure,
    v_success,
)


@given(x=st.integers())
def test_identity(x: int) -> None:
    v = v_success(x)
    assert v_ap(v_success(lambda n: n), v) == v


@given(x=st.integers())
def test_homomorphism(x: int) -> None:
    def f(n: int) -> int:
        return n + 10

    assert v_ap(v_success(f), v_success(x)) == v_success(f(x))


@given(x=st.integers())
def test_interchange(x: int) -> None:
    u = v_success(lambda n: n * 3)
    assert v_ap(u, v_success(x)) == v_ap(v_success(lambda f: f(x)), u)


@given(x=st.integers())
def test_composition(x: int) -> None:
    def f(n: int) -> int:
        return n + 1

    def g(n: int) -> int:
        return n * 2

    u = v_success(f)
    v = v_success(g)
    w = v_success(x)
    left = v_ap(v_ap(v_ap(v_success(compose), u), v), w)
    right = v_ap(u, v_ap(v, w))
    assert left == right


@given(errs1=st.lists(st.text(), min_size=1), errs2=st.lists(st.text(), min_size=1))
def test_collects_all_errors_concat(errs1: list[str], errs2: list[str]) -> None:
    bad_f: Validation[Callable[[int], int], str] = cast(
        Validation[Callable[[int], int], str], v_failure(errs1)
    )
    bad_x: Validation[int, str] = cast(Validation[int, str], v_failure(errs2))
    result = v_ap(bad_f, bad_x)
    assert isinstance(result, VFailure)
    assert result.errors == tuple(errs1 + errs2)


@given(errs1=st.lists(st.text(), min_size=1), errs2=st.lists(st.text(), min_size=1))
def test_dedup_stable(errs1: list[str], errs2: list[str]) -> None:
    combined = dedup_stable(tuple(errs1), tuple(errs2))
    seen = set()
    expected = []
    for e in errs1 + errs2:
        if e not in seen:
            seen.add(e)
            expected.append(e)
    assert combined == tuple(expected)


def test_v_failure_rejects_empty() -> None:
    with pytest.raises(ValueError):
        v_failure([])
