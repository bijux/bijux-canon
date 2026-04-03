# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import hypothesis.strategies as st
from hypothesis import given, settings

from bijux_rag.fp.effects.layering import transpose_option_result, transpose_result_option
from bijux_rag.result.types import Err, NoneVal, Ok, Option, Result, Some

settings.register_profile("ci", max_examples=300, derandomize=True, deadline=None)
settings.load_profile("ci")


def st_value() -> st.SearchStrategy[int]:
    return st.integers(-20, 20)


def st_error() -> st.SearchStrategy[str]:
    return st.text(min_size=0, max_size=8)


def st_option() -> st.SearchStrategy[Option[int]]:
    return st.one_of(st.builds(Some, st_value()), st.builds(NoneVal))


def st_result_option() -> st.SearchStrategy[Result[Option[int], str]]:
    return st.one_of(st.builds(Ok, st_option()), st.builds(Err, st_error()))


@given(ro=st_result_option())
def test_transpose_involution_result_option(ro: Result[Option[int], str]) -> None:
    assert transpose_option_result(transpose_result_option(ro)) == ro


def test_error_dominates_absence_result_option() -> None:
    assert transpose_result_option(Err("x")) == Some(Err("x"))
    assert transpose_option_result(Some(Err("x"))) == Err("x")
