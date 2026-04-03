# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import asyncio

from bijux_rag.domain.effects.async_ import AsyncPlan, async_gather
from bijux_rag.infra.adapters.async_runtime import perform_async
from bijux_rag.result.types import Err, ErrInfo, Ok, Result


def test_async_gather_preserves_input_order() -> None:
    async def run() -> None:
        def mk_plan(i: int) -> AsyncPlan[int]:
            async def _coro() -> Result[int, ErrInfo]:
                await asyncio.sleep((5 - i) * 0.0005)
                return Ok(i)

            return lambda: _coro()

        plan = async_gather([mk_plan(i) for i in range(1, 6)], concurrency=2)
        res = await perform_async(plan)
        assert res == Ok([1, 2, 3, 4, 5])

    asyncio.run(run())


def test_async_gather_never_exceeds_concurrency_limit() -> None:
    async def run() -> None:
        in_flight = 0
        max_seen = 0

        def mk_plan(i: int) -> AsyncPlan[int]:
            async def _coro() -> Result[int, ErrInfo]:
                nonlocal in_flight, max_seen
                in_flight += 1
                max_seen = max(max_seen, in_flight)
                await asyncio.sleep(0)
                in_flight -= 1
                return Ok(i)

            return lambda: _coro()

        concurrency = 3
        res = await perform_async(
            async_gather([mk_plan(i) for i in range(50)], concurrency=concurrency)
        )
        assert isinstance(res, Ok)
        assert max_seen <= concurrency

    asyncio.run(run())


def test_async_gather_returns_first_error_by_index() -> None:
    async def run() -> None:
        def err_plan(code: str, delay: float) -> AsyncPlan[int]:
            async def _coro() -> Result[int, ErrInfo]:
                await asyncio.sleep(delay)
                return Err(ErrInfo(code=code, msg="boom"))

            return lambda: _coro()

        def ok_plan(i: int) -> AsyncPlan[int]:
            async def _coro() -> Result[int, ErrInfo]:
                return Ok(i)

            return lambda: _coro()

        # Error at index 0 is slower, but should be selected deterministically.
        plans: list[AsyncPlan[int]] = [
            err_plan("E0", delay=0.01),
            ok_plan(1),
            err_plan("E2", delay=0.0),
        ]
        res = await perform_async(async_gather(plans, concurrency=3))
        assert isinstance(res, Err)
        assert res.error.code == "E0"

    asyncio.run(run())
