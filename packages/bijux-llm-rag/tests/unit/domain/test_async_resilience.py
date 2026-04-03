# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import asyncio
import warnings
from random import Random

from hypothesis import given, settings
from hypothesis import strategies as st

from bijux_rag.domain.effects.async_ import (
    FakeClock,
    ResilienceEnv,
    RetryPolicy,
    TimeoutPolicy,
    async_with_resilience,
    make_fake_timeout_ctx,
)
from bijux_rag.result.types import Err, ErrInfo, Ok


def test_identity_when_no_retry_no_timeout() -> None:
    async def run() -> None:
        async def step():
            return Ok(42)

        def base_plan():
            return step()

        plan = async_with_resilience(base_plan, RetryPolicy(max_attempts=1), None)
        assert plan is base_plan
        assert await plan() == Ok(42)

    asyncio.run(run())


@given(attempts=st.integers(min_value=2, max_value=10))
@settings(deadline=None, max_examples=50)
def test_retry_bounded_attempts(attempts: int) -> None:
    async def run() -> None:
        policy = RetryPolicy(max_attempts=attempts, retriable_codes=frozenset({"TRANSIENT"}))
        call_count = 0

        async def always_fail():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0)
            return Err(ErrInfo(code="TRANSIENT", msg="fail"))

        plan = async_with_resilience(lambda: always_fail(), policy, None)
        res = await plan()

        assert isinstance(res, Err) and res.error.code == "MAX_RETRIES"
        assert call_count == attempts

    asyncio.run(run())


@given(base_ms=st.integers(min_value=50, max_value=500))
@settings(deadline=None, max_examples=50)
def test_backoff_cap_respected(base_ms: int) -> None:
    async def run() -> None:
        policy = RetryPolicy(
            max_attempts=6, backoff_base_ms=base_ms, max_backoff_ms=1000, jitter_factor=0.0
        )

        delays: list[float] = []

        async def fake_sleep(d: float) -> None:
            delays.append(d)

        env = ResilienceEnv(rng=Random(42), sleep=fake_sleep, clock=FakeClock())

        async def force_retry():
            return Err(ErrInfo(code="TRANSIENT", msg="retry"))

        plan = async_with_resilience(lambda: force_retry(), policy, None, env)
        await plan()

        for attempt, delay in enumerate(delays, start=1):
            expected = min(base_ms * (2 ** (attempt - 1)), policy.max_backoff_ms) / 1000.0
            assert abs(delay - expected) < 1e-9

    asyncio.run(run())


def test_timeout_triggers_correctly_with_fake_clock() -> None:
    async def run() -> None:
        clock = FakeClock()

        async def advancing_sleep(seconds: float) -> None:
            clock.advance_s(seconds)
            await asyncio.sleep(0)

        env = ResilienceEnv(rng=Random(0), sleep=advancing_sleep, clock=clock)
        timeout_ctx = make_fake_timeout_ctx(clock)

        timeout_policy = TimeoutPolicy(timeout_ms=50)

        async def hanging():
            await env.sleep(0.1)
            return Ok("never")

        plan = async_with_resilience(
            lambda: hanging(),
            RetryPolicy(max_attempts=1, retriable_codes=frozenset({"TIMEOUT"})),
            timeout_policy,
            env,
            timeout_ctx=timeout_ctx,
        )
        res = await plan()

        assert isinstance(res, Err) and res.error.code == "TIMEOUT"
        assert clock.now_s() >= 0.05

    asyncio.run(run())


def test_non_idempotent_warning() -> None:
    async def run() -> None:
        policy = RetryPolicy(
            max_attempts=3, retriable_codes=frozenset({"TRANSIENT"}), idempotent=False
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            async def side_effect():
                return Err(ErrInfo(code="TRANSIENT", msg="retry me"))

            plan = async_with_resilience(lambda: side_effect(), policy, None)
            await plan()

            assert len(w) == 1
            assert "non-idempotent" in str(w[0].message)

    asyncio.run(run())
