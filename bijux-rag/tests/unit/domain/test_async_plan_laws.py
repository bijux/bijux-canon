# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import asyncio

from hypothesis import given, settings
from hypothesis import strategies as st

from bijux_rag.domain.effects.async_ import async_bind, async_pure
from bijux_rag.infra.adapters.async_runtime import perform_async


@given(x=st.integers())
@settings(max_examples=100)
def test_async_plan_left_identity(x: int) -> None:
    async def run() -> None:
        def f(y: int):
            return async_pure(y + 1)

        assert await perform_async(async_bind(async_pure(x), f)) == await perform_async(f(x))

    asyncio.run(run())


@given(x=st.integers())
@settings(max_examples=100)
def test_async_plan_right_identity(x: int) -> None:
    async def run() -> None:
        plan = async_pure(x)
        assert await perform_async(async_bind(plan, async_pure)) == await perform_async(plan)

    asyncio.run(run())


@given(x=st.integers())
@settings(max_examples=100)
def test_async_plan_associativity(x: int) -> None:
    async def run() -> None:
        a = async_pure(x)

        def f(y: int):
            return async_pure(y + 1)

        def g(z: int):
            return async_pure(z * 2)

        left = await perform_async(async_bind(async_bind(a, f), g))
        right = await perform_async(async_bind(a, lambda y: async_bind(f(y), g)))
        assert left == right

    asyncio.run(run())


def test_async_plan_replayable() -> None:
    async def run() -> None:
        plan = async_bind(async_pure(1), lambda x: async_pure(x + 1))
        r1 = await perform_async(plan)
        r2 = await perform_async(plan)
        assert r1 == r2

    asyncio.run(run())
