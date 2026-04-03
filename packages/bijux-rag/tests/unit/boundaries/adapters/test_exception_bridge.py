# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest

from bijux_rag.boundaries.adapters.exception_bridge import (
    UnexpectedFailure,
    result_map_try,
    try_result,
    unexpected_fail,
    v_map_try,
    v_try,
)
from bijux_rag.fp.core import VFailure, VSuccess
from bijux_rag.result.types import Err, Ok


def test_try_result_catches_configured_exception() -> None:
    def boom() -> int:
        raise ZeroDivisionError("nope")

    r = try_result(boom, lambda ex: type(ex).__name__, exc_type=ZeroDivisionError)
    assert r == Err("ZeroDivisionError")


def test_try_result_does_not_catch_baseexception_by_default() -> None:
    def boom() -> int:
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        try_result(boom, lambda ex: type(ex).__name__)


def test_result_map_try_maps_value_and_catches_expected_exception() -> None:
    def f(x: int) -> int:
        if x == 0:
            raise ValueError("bad")
        return 10 // x

    ok = result_map_try(Ok(2), f, lambda ex: str(ex), exc_type=ValueError)
    assert ok == Ok(5)

    err = result_map_try(Ok(0), f, lambda ex: str(ex), exc_type=ValueError)
    assert err == Err("bad")


def test_v_try_and_v_map_try_bridge_exceptions() -> None:
    def boom() -> int:
        raise ValueError("x")

    v1 = v_try(boom, lambda ex: str(ex), exc_type=ValueError)
    assert v1 == VFailure(("x",))

    v2 = v_map_try(VSuccess(1), lambda _: boom(), lambda ex: str(ex), exc_type=ValueError)
    assert v2 == VFailure(("x",))


def test_unexpected_fail_raises() -> None:
    with pytest.raises(UnexpectedFailure):
        unexpected_fail("fatal")
