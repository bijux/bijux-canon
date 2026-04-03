# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import asyncio

from hypothesis import given, settings
from hypothesis import strategies as st

from bijux_rag.domain.effects.async_ import ChunkPolicy, FakeSleeper, async_gen_chunk
from bijux_rag.result.types import Ok


@given(items=st.lists(st.integers(), max_size=200))
@settings(deadline=None, max_examples=50)
def test_chunk_order_completeness_size(items: list[int]) -> None:
    async def run() -> None:
        policy = ChunkPolicy[int](max_units=10, max_delay_ms=1000)
        sleeper = FakeSleeper()

        async def source():
            for i in items:
                yield Ok(i)

        chunked = async_gen_chunk(lambda: source(), policy)(sleeper)

        emitted: list[int] = []
        async for batch_res in chunked():
            assert isinstance(batch_res, Ok)
            batch = batch_res.value
            assert len(batch) <= policy.max_units or policy.max_units == 0
            emitted.extend(batch)

        assert emitted == items

    asyncio.run(run())


@given(items=st.lists(st.integers(), max_size=50))
@settings(deadline=None, max_examples=25)
def test_chunk_time_bound(items: list[int]) -> None:
    async def run() -> None:
        policy = ChunkPolicy[int](max_units=1000, max_delay_ms=200)
        sleeper = FakeSleeper()

        item_arrival_ts: list[int] = []

        async def source():
            for i in items:
                item_arrival_ts.append(sleeper.now_ms())
                await sleeper.sleep_ms(30)
                yield Ok(i)

        chunked = async_gen_chunk(lambda: source(), policy)(sleeper)

        batch_first_ts: list[int] = []
        batch_emit_ts: list[int] = []

        async for batch_res in chunked():
            assert isinstance(batch_res, Ok)
            batch_emit_ts.append(sleeper.now_ms())
            if item_arrival_ts:
                batch_first_ts.append(item_arrival_ts[0])
                del item_arrival_ts[: len(batch_res.value)]

        for first_ts, emit_ts in zip(batch_first_ts, batch_emit_ts):
            assert (emit_ts - first_ts) <= policy.max_delay_ms + 40

    asyncio.run(run())
