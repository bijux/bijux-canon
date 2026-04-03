# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

from bijux_rag.domain.effects.async_ import AsyncGen, async_gen_gather
from bijux_rag.result.types import Err, ErrInfo, Ok, Result
from tests.helpers import collect


def test_async_gen_gather_yields_all_items() -> None:
    async def run() -> None:
        def g1() -> AsyncGen[int]:
            async def _gen() -> AsyncIterator[Result[int, ErrInfo]]:
                for x in [1, 2, 3]:
                    await asyncio.sleep(0)
                    yield Ok(x)

            return lambda: _gen()

        def g2() -> AsyncGen[int]:
            async def _gen() -> AsyncIterator[Result[int, ErrInfo]]:
                for x in [10, 20]:
                    await asyncio.sleep(0)
                    yield Ok(x)

            return lambda: _gen()

        merged = async_gen_gather([g1(), g2()], max_buffer=2)
        out = await collect(merged)
        values = sorted([x.value for x in out if isinstance(x, Ok)])
        assert values == [1, 2, 3, 10, 20]

    asyncio.run(run())


def test_async_gen_gather_propagates_err_items() -> None:
    async def run() -> None:
        def src() -> AsyncGen[int]:
            async def _gen() -> AsyncIterator[Result[int, ErrInfo]]:
                yield Ok(1)
                yield Err(ErrInfo(code="BOOM", msg="test"))
                yield Ok(2)

            return lambda: _gen()

        merged = async_gen_gather([src()], max_buffer=1)
        out = await collect(merged)
        assert isinstance(out[1], Err) and out[1].error.code == "BOOM"

    asyncio.run(run())


def test_async_gen_gather_closes_sources_on_early_break() -> None:
    async def run() -> None:
        @dataclass
        class Tracker:
            closed: int = 0

        tracker = Tracker()

        def src() -> AsyncGen[int]:
            async def _gen() -> AsyncIterator[Result[int, ErrInfo]]:
                try:
                    i = 0
                    while True:
                        yield Ok(i)
                        i += 1
                        await asyncio.sleep(0)
                finally:
                    tracker.closed += 1

            return lambda: _gen()

        merged = async_gen_gather([src()], max_buffer=1)

        it = merged()
        async for _ in it:
            break
        await it.aclose()

        assert tracker.closed == 1

    asyncio.run(run())
