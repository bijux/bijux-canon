# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import asyncio

from hypothesis import given, settings
from hypothesis import strategies as st

from bijux_rag.domain.effects.async_ import (
    AsyncGen,
    BackpressurePolicy,
    async_gen_bounded_map,
    async_lift,
    async_pure,
)
from bijux_rag.result.types import Err, ErrInfo, Ok, Result


def async_gen_from_ok_list(xs: list[int]) -> AsyncGen[int]:
    async def _src():
        for x in xs:
            yield Ok(x)

    return lambda: _src()


@given(
    n=st.integers(min_value=20, max_value=200), concurrency=st.integers(min_value=1, max_value=20)
)
@settings(deadline=None, max_examples=50)
def test_bounded_concurrency_never_exceeds_limit(n: int, concurrency: int) -> None:
    async def run() -> None:
        policy = BackpressurePolicy(max_concurrent=concurrency, ordered=True)

        in_flight = 0
        max_seen = 0

        async def probe(x: int) -> Result[int, ErrInfo]:
            nonlocal in_flight, max_seen
            in_flight += 1
            max_seen = max(max_seen, in_flight)
            await asyncio.sleep(0)
            in_flight -= 1
            return Ok(x)

        src = async_gen_from_ok_list(list(range(n)))
        stream = async_gen_bounded_map(src, lambda x: async_lift(lambda: probe(x)), policy)

        async for _ in stream():
            pass

        assert max_seen <= concurrency

    asyncio.run(run())


@given(xs=st.lists(st.integers(), max_size=100))
@settings(deadline=None, max_examples=100)
def test_bounded_equivalence_to_unbounded_when_concurrency_large(xs: list[int]) -> None:
    async def run() -> None:
        policy = BackpressurePolicy(max_concurrent=len(xs) + 10, ordered=True)
        src = async_gen_from_ok_list(xs)
        bounded = [
            r.value
            async for r in async_gen_bounded_map(src, async_pure, policy)()
            if isinstance(r, Ok)
        ]
        assert bounded == xs

    asyncio.run(run())


def test_bounded_ordered_preserves_order_under_stragglers() -> None:
    async def run() -> None:
        policy = BackpressurePolicy(max_concurrent=3, ordered=True)

        async def worker(x: int) -> Result[int, ErrInfo]:
            await asyncio.sleep((5 - x) * 0.001)
            return Ok(x)

        src = async_gen_from_ok_list([1, 2, 3, 4, 5])
        results = [
            r.value
            async for r in async_gen_bounded_map(
                src, lambda x: async_lift(lambda: worker(x)), policy
            )()
            if isinstance(r, Ok)
        ]
        assert results == [1, 2, 3, 4, 5]

    asyncio.run(run())


def test_bounded_err_propagation_without_calling_f() -> None:
    async def run() -> None:
        call_args: list[int] = []

        async def f(x: int) -> Result[str, ErrInfo]:
            call_args.append(x)
            await asyncio.sleep(0)
            return Ok(str(x))

        async def _src():
            yield Ok(1)
            yield Err(ErrInfo(code="BOOM", msg="test"))
            yield Ok(2)

        def src() -> AsyncGen[int]:
            return lambda: _src()

        stream = async_gen_bounded_map(
            src(), lambda x: async_lift(lambda: f(x)), BackpressurePolicy(ordered=True)
        )

        results = [r async for r in stream()]

        assert call_args == [1, 2]
        assert isinstance(results[1], Err) and results[1].error.code == "BOOM"

    asyncio.run(run())


def test_bounded_unordered_cancels_pending_tasks_on_early_close() -> None:
    async def run() -> None:
        started = 0
        finished = 0
        cancelled = 0
        gate = asyncio.Event()

        async def step(i: int) -> Result[int, ErrInfo]:
            nonlocal started, finished, cancelled
            started += 1
            try:
                if i == 0:
                    await asyncio.sleep(0)
                    return Ok(i)
                try:
                    await gate.wait()
                    return Ok(i)
                except asyncio.CancelledError:
                    cancelled += 1
                    raise
            finally:
                finished += 1

        async def _src():
            for i in range(10):
                yield Ok(i)

        def src() -> AsyncGen[int]:
            return lambda: _src()

        stream = async_gen_bounded_map(
            src(),
            lambda x: async_lift(lambda: step(x)),
            BackpressurePolicy(max_concurrent=4, ordered=False),
        )

        it = stream()
        first = await anext(it)
        assert first == Ok(0)
        await it.aclose()

        assert started >= 2
        assert cancelled >= 1
        assert finished == started

    asyncio.run(run())
