# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import contextlib

import pytest
from hypothesis import given
from hypothesis import strategies as st

from bijux_rag.policies.breakers import short_circuit_on_err_truncate
from bijux_rag.policies.resources import managed_stream, nested_managed, with_resource_stream
from bijux_rag.result import Err, Ok


def test_cleanup_on_normal_exhaustion() -> None:
    closed = False

    def gen():
        nonlocal closed
        try:
            yield 1
            yield 2
        finally:
            closed = True

    with with_resource_stream(gen()) as it:
        list(it)
    assert closed


def test_cleanup_on_consumer_exception() -> None:
    closed = False

    def gen():
        nonlocal closed
        try:
            yield 1
            yield 2
        finally:
            closed = True

    with with_resource_stream(gen()) as it:
        with pytest.raises(ValueError):
            for x in it:
                if x == 2:
                    raise ValueError("boom")
    assert closed


def test_cleanup_on_partial_iteration() -> None:
    closed = False

    def gen():
        nonlocal closed
        try:
            yield from range(1000)
        finally:
            closed = True

    with with_resource_stream(gen()) as it:
        for _ in range(10):
            next(it)
    assert closed


def test_cleanup_on_producer_exception() -> None:
    closed = False

    def gen():
        nonlocal closed
        try:
            yield 1
            raise ValueError("producer fail")
        finally:
            closed = True

    with with_resource_stream(gen()) as it:
        with pytest.raises(ValueError):
            list(it)
    assert closed


def test_manager_lazy_entry() -> None:
    entered = False

    def factory():
        nonlocal entered
        entered = True
        return iter([42])

    mgr = managed_stream(factory)
    assert not entered
    with mgr as it:
        assert entered
        assert next(it) == 42


@given(items=st.lists(st.integers()))
def test_cleanup_on_break(items: list[int]) -> None:
    closed = False

    def src():
        nonlocal closed
        try:
            for x in items:
                yield Ok(x) if x != 0 else Err("ZERO")
        finally:
            closed = True

    with with_resource_stream(src()) as s:
        list(short_circuit_on_err_truncate(s))
    assert closed


def test_nested_manager_lifo() -> None:
    order: list[str] = []

    def m1():
        order.append("enter1")
        yield "a"
        order.append("exit1")

    def m2():
        order.append("enter2")
        yield "b"
        order.append("exit2")

    with nested_managed([contextlib.contextmanager(m1)(), contextlib.contextmanager(m2)()]) as (
        _a,
        _b,
    ):
        pass
    assert order == ["enter1", "enter2", "exit2", "exit1"]


def test_managed_equivalence() -> None:
    def factory():
        yield from range(10)

    with managed_stream(factory) as it:
        assert list(it) == list(range(10))
