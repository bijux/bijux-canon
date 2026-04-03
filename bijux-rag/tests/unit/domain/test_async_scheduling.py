# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import asyncio
from random import Random

from hypothesis import given, settings
from hypothesis import strategies as st

from bijux_rag.domain.effects.async_ import (
    FairnessPolicy,
    FakeClock,
    RateLimitPolicy,
    ResilienceEnv,
    async_gen_fair_merge,
    async_gen_from_list,
    async_gen_rate_limited,
)
from bijux_rag.result.types import Ok


@given(
    tps=st.floats(min_value=0.5, max_value=50.0, allow_nan=False, allow_infinity=False),
    burst=st.integers(min_value=1, max_value=50),
    n=st.integers(min_value=50, max_value=500),
)
@settings(deadline=None, max_examples=30)
def test_token_bucket_never_exceeds_policy(tps: float, burst: int, n: int) -> None:
    async def run() -> None:
        policy = RateLimitPolicy(tokens_per_second=tps, burst_tokens=burst)
        clock = FakeClock()

        async def fake_sleep(s: float) -> None:
            clock.advance_s(s)

        env = ResilienceEnv(clock=clock, sleep=fake_sleep, rng=Random(0))

        emission_times: list[float] = []
        src = async_gen_from_list(list(range(n)))
        stream = async_gen_rate_limited(src, policy, env=env)

        async for _ in stream():
            emission_times.append(clock.now_s())

        elapsed = clock.now_s()
        assert n <= (elapsed * tps) + burst + 1

        right = 0
        for i, start in enumerate(emission_times):
            end = start + 1.0
            while right < len(emission_times) and emission_times[right] <= end:
                right += 1
            items_in_window = right - i
            assert items_in_window <= tps * 1.0 + burst + 1

    asyncio.run(run())


@given(
    total=st.integers(min_value=1000, max_value=5000),
    weight_a=st.integers(min_value=1, max_value=10),
    weight_b=st.integers(min_value=1, max_value=10),
)
@settings(deadline=None, max_examples=20)
def test_fair_merge_approx_proportional_when_all_ready(
    total: int, weight_a: int, weight_b: int
) -> None:
    async def run() -> None:
        policy = FairnessPolicy(weights={0: weight_a, 1: weight_b}, max_buffer_per_stream=32)

        def instant_producer(tag: str, count: int):
            async def _gen():
                for i in range(count):
                    yield Ok(f"{tag}{i}")

            return lambda: _gen()

        merged = async_gen_fair_merge(
            [instant_producer("A", total * 10), instant_producer("B", total * 10)], policy
        )

        counts = {"A": 0, "B": 0}
        async for item in merged():
            if isinstance(item, Ok):
                counts[item.value[0]] += 1
                if sum(counts.values()) >= total:
                    break

        expected_ratio_b = weight_b / (weight_a + weight_b)
        actual_ratio_b = counts["B"] / sum(counts.values())
        assert abs(actual_ratio_b - expected_ratio_b) <= 0.02
        assert min(counts.values()) >= total // (weight_a + weight_b) - 10

    asyncio.run(run())


@given(
    weight_a=st.integers(min_value=1, max_value=10),
    weight_b=st.integers(min_value=1, max_value=10),
    n=st.integers(min_value=200, max_value=2000),
)
@settings(deadline=None, max_examples=25)
def test_fair_merge_prefix_normalized_gap_bounded(weight_a: int, weight_b: int, n: int) -> None:
    async def run() -> None:
        policy = FairnessPolicy(weights={0: weight_a, 1: weight_b}, max_buffer_per_stream=64)

        def infinite(tag: str):
            async def _gen():
                i = 0
                while True:
                    yield Ok(f"{tag}{i}")
                    i += 1

            return lambda: _gen()

        merged = async_gen_fair_merge([infinite("A"), infinite("B")], policy)
        it = merged()

        a = 0
        b = 0
        max_gap = 0.0
        for _ in range(n):
            item = await anext(it)
            assert isinstance(item, Ok)
            if item.value[0] == "A":
                a += 1
            else:
                b += 1
            gap = abs((a / weight_a) - (b / weight_b))
            max_gap = max(max_gap, gap)

        await it.aclose()

        assert max_gap <= 1.0 + 1e-9

    asyncio.run(run())


def test_fair_merge_closes_sources_on_early_break() -> None:
    async def run() -> None:
        closed = [0, 0]

        def src(idx: int):
            async def _gen():
                try:
                    i = 0
                    while True:
                        yield Ok((idx, i))
                        i += 1
                        await asyncio.sleep(0)
                finally:
                    closed[idx] += 1

            return lambda: _gen()

        merged = async_gen_fair_merge([src(0), src(1)], FairnessPolicy(max_buffer_per_stream=4))

        it = merged()
        async for _ in it:
            break
        await it.aclose()

        assert closed == [1, 1]

    asyncio.run(run())
