# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias, TypeVar

from hypothesis import given
from hypothesis import strategies as st
from typing_extensions import assert_never

from bijux_rag.fp.core import NoneVal, Some
from bijux_rag.fp.error import ErrorCode
from bijux_rag.result.types import Err, ErrInfo, Ok, Result

T = TypeVar("T")
E = TypeVar("E")

Option: TypeAlias = Some[T] | NoneVal


def unwrap_or(opt: Option[T], default: T) -> T:
    match opt:
        case Some(value=v):
            return v
        case NoneVal():
            return default
        case other:
            assert_never(other)


@given(v=st.integers())
def test_option_unwrap_or_some(v: int) -> None:
    assert unwrap_or(Some(v), default=-1) == v


@given(default=st.integers())
def test_option_unwrap_or_none(default: int) -> None:
    assert unwrap_or(NoneVal(), default=default) == default


@dataclass(frozen=True)
class DummyErr:
    code: ErrorCode
    msg: str


def handle_result(res: Result[T, DummyErr]) -> T | None:
    match res:
        case Ok(value=v):
            return v
        case Err(error=_):
            return None
        case other:
            assert_never(other)


@given(
    res=st.one_of(
        st.builds(Ok, st.integers()),
        st.builds(Err, st.builds(DummyErr, code=st.sampled_from(list(ErrorCode)), msg=st.text())),
    )
)
def test_result_match_exhaustive(res: Result[int, DummyErr]) -> None:
    _ = handle_result(res)


def classify_err(e: ErrInfo) -> str:
    match e:
        case ErrInfo(code=code, msg=_):
            return code
        case other:
            assert_never(other)


@given(code=st.text(), msg=st.text())
def test_errinfo_match_is_total(code: str, msg: str) -> None:
    assert classify_err(ErrInfo(code=code, msg=msg)) == code
