# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

from bijux_rag.domain.effects.async_ import (
    lift_sync,
    lift_sync_gen_with_executor,
    lift_sync_with_executor,
)
from bijux_rag.infra.adapters.async_runtime import perform_async
from bijux_rag.result.types import Err, ErrInfo, Ok, Result


def good(x: int) -> Result[int, ErrInfo]:
    return Ok(x + 1)


def bad(_: int) -> Result[int, ErrInfo]:
    raise RuntimeError("boom")


def test_lift_sync_wraps_exception() -> None:
    async def run() -> None:
        plan = lift_sync(bad)(1)
        res = await perform_async(plan)
        assert isinstance(res, Err)
        assert res.error.code == "UNEXPECTED"

    asyncio.run(run())


def test_lift_sync_with_executor_runs_in_executor() -> None:
    async def run() -> None:
        with ThreadPoolExecutor(max_workers=1) as ex:
            plan = lift_sync_with_executor(good, ex)(1)
            res = await perform_async(plan)
            assert res == Ok(2)

    asyncio.run(run())


def test_lift_sync_gen_with_executor_yields_items() -> None:
    async def run() -> None:
        def make_list(x: int) -> Result[list[int], ErrInfo]:
            return Ok([x, x + 1])

        with ThreadPoolExecutor(max_workers=1) as ex:
            gen = lift_sync_gen_with_executor(make_list, ex)(1)
            out = [r async for r in gen()]
            assert out == [Ok(1), Ok(2)]

    asyncio.run(run())
