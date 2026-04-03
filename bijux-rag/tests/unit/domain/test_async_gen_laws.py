# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from hypothesis import given, settings
from hypothesis import strategies as st

from bijux_rag.domain.effects.async_ import (
    async_gen_and_then,
    async_gen_map,
    async_gen_return,
    async_gen_using,
)
from bijux_rag.result.types import Err, ErrInfo, Ok
from tests.helpers import collect


@given(x=st.integers())
@settings(max_examples=100)
def test_async_gen_left_identity(x: int) -> None:
    async def run() -> None:
        def f(y: int):
            return async_gen_return(y + 1)

        left = await collect(async_gen_and_then(async_gen_return(x), f))
        right = await collect(f(x))
        assert left == right

    asyncio.run(run())


@given(xs=st.lists(st.integers(), max_size=50))
@settings(max_examples=100)
def test_async_gen_right_identity(xs: list[int]) -> None:
    async def run() -> None:
        async def _src():
            for v in xs:
                yield Ok(v)

        def src():
            return lambda: _src()

        left = await collect(async_gen_and_then(src(), async_gen_return))
        right = await collect(src())
        assert left == right

    asyncio.run(run())


@given(xs=st.lists(st.integers(), max_size=50))
@settings(max_examples=100)
def test_async_gen_associativity(xs: list[int]) -> None:
    async def run() -> None:
        async def _src():
            for v in xs:
                yield Ok(v)

        def src():
            return lambda: _src()

        def f(y: int):
            return async_gen_return(y + 1)

        def g(z: int):
            return async_gen_return(z * 2)

        a = async_gen_and_then(async_gen_and_then(src(), f), g)
        b = async_gen_and_then(src(), lambda y: async_gen_and_then(f(y), g))

        a_items = [item.value async for item in a() if isinstance(item, Ok)]
        b_items = [item.value async for item in b() if isinstance(item, Ok)]
        assert a_items == b_items

    asyncio.run(run())


def test_async_gen_per_item_error_propagation() -> None:
    async def run() -> None:
        async def _src():
            yield Ok(1)
            yield Err(ErrInfo(code="BOOM", msg="test"))
            yield Ok(2)

        def src():
            return lambda: _src()

        out = await collect(async_gen_map(src(), lambda x: x * 10))
        assert out[0] == Ok(10)
        assert isinstance(out[1], Err) and out[1].error.code == "BOOM"
        assert out[2] == Ok(20)

    asyncio.run(run())


def test_async_gen_replayable() -> None:
    async def run() -> None:
        gen = async_gen_return(1)
        first = await collect(gen)
        second = await collect(gen)
        assert first == second

    asyncio.run(run())


def test_async_gen_using_closes_on_early_break() -> None:
    async def run() -> None:
        @dataclass
        class Tracker:
            entered: int = 0
            exited: int = 0

        tracker = Tracker()

        class CM:
            async def __aenter__(self) -> Tracker:
                tracker.entered += 1
                return tracker

            async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
                tracker.exited += 1

        def make_stream(_: Tracker):
            return async_gen_return(1)

        gen = async_gen_using(lambda: CM(), make_stream)

        it = gen()
        async for _ in it:
            break
        await it.aclose()

        assert tracker.entered == 1
        assert tracker.exited == 1

    asyncio.run(run())
