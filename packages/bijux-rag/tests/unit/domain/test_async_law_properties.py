# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import asyncio

from hypothesis import given, settings
from hypothesis import strategies as st

from bijux_rag.domain.effects.async_ import (
    AsyncGen,
    AsyncPlan,
    RetryPolicy,
    async_bind,
    async_gen_from_list,
    async_gen_map_action,
    async_with_resilience,
)
from bijux_rag.result.types import Err, ErrInfo, Ok, Result


class FakeEmbedder:
    def __init__(self, schedule: list[bool]) -> None:
        self._schedule = schedule
        self._idx = 0

    def reset_schedule(self, schedule: list[bool]) -> None:
        self._schedule = schedule
        self._idx = 0

    def embed(self, key: int) -> AsyncPlan[int]:
        async def _act() -> Result[int, ErrInfo]:
            await asyncio.sleep(0)
            should_fail = self._schedule[self._idx] if self._idx < len(self._schedule) else True
            self._idx += 1
            if should_fail:
                return Err(ErrInfo(code="TRANSIENT", msg="fail", path=(key,)))
            return Ok(key)

        return lambda: _act()


class FakeVectorStore:
    def __init__(self) -> None:
        self.data: dict[int, int] = {}
        self.open_connections = 0

    def reset(self) -> None:
        self.data.clear()
        self.open_connections = 0

    def snapshot(self) -> dict[int, int]:
        return dict(self.data)

    def upsert(self, key: int) -> AsyncPlan[int]:
        async def _act() -> Result[int, ErrInfo]:
            self.open_connections += 1
            try:
                self.data[key] = key
                await asyncio.sleep(0)
                return Ok(key)
            finally:
                self.open_connections -= 1

        return lambda: _act()


def lawful_desc(
    keys: list[int],
    embedder: FakeEmbedder,
    store: FakeVectorStore,
    retry: RetryPolicy,
) -> AsyncGen[int]:
    def process(key: int) -> AsyncPlan[int]:
        plan = async_with_resilience(embedder.embed(key), retry, None)
        return async_bind(plan, lambda _: store.upsert(key))

    return async_gen_map_action(async_gen_from_list(keys), process)


@given(
    keys=st.lists(st.integers(min_value=0, max_value=1000), min_size=0, max_size=50, unique=True),
    schedule=st.lists(st.booleans(), min_size=0, max_size=200),
)
@settings(deadline=None, max_examples=25)
def test_async_pipeline_idempotence_and_no_duplication(
    keys: list[int], schedule: list[bool]
) -> None:
    async def run() -> None:
        schedule_local = schedule[: len(keys) * 3] + [True] * max(
            0, (len(keys) * 3 - len(schedule))
        )

        embedder = FakeEmbedder(schedule=schedule_local)
        store = FakeVectorStore()
        retry = RetryPolicy(max_attempts=3, retriable_codes=frozenset({"TRANSIENT"}))

        desc = lawful_desc(keys, embedder, store, retry)
        emitted1 = [r async for r in desc()]
        state1 = store.snapshot()

        store.reset()
        embedder.reset_schedule(schedule_local)
        emitted2 = [r async for r in desc()]
        state2 = store.snapshot()

        assert emitted2 == emitted1
        assert state2 == state1

        ok_keys = [r.value for r in emitted1 if isinstance(r, Ok)]
        all_keys = [r.value if isinstance(r, Ok) else r.error.path[0] for r in emitted1]
        assert len(ok_keys) == len(set(ok_keys))
        assert len(all_keys) == len(set(all_keys))

    asyncio.run(run())


@given(
    keys=st.lists(st.integers(min_value=0, max_value=1000), min_size=0, max_size=30, unique=True)
)
@settings(deadline=None, max_examples=25)
def test_async_pipeline_partial_cancellation_safety(keys: list[int]) -> None:
    async def run() -> None:
        embedder = FakeEmbedder(schedule=[False] * (len(keys) + 10))
        store = FakeVectorStore()
        retry = RetryPolicy(max_attempts=1)

        desc = lawful_desc(keys, embedder, store, retry)

        ait = desc()
        consumed = 0
        try:
            async for _ in ait:
                consumed += 1
                if consumed >= len(keys) // 2:
                    break
        finally:
            await ait.aclose()

        assert len(store.data) == consumed
        assert store.open_connections == 0

    asyncio.run(run())
