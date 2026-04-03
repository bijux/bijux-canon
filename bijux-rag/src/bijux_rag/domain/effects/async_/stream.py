# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG: AsyncGen – streaming async effect descriptions (end-of-Bijux RAG).

This module groups the "core stream" primitives for Bijux RAG:
- `AsyncGen[T]`: a replayable thunk returning an async iterator of `Result[T, ErrInfo]`
- monadic composition (`async_gen_and_then`, `async_gen_map`, …)
- safe resource usage (`async_gen_using`)
- fan-in (`async_gen_gather`) with bounded buffering
- batching/chunking (`async_gen_chunk`) with a pluggable clock/sleeper
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from time import monotonic
from typing import Generic, Protocol, TypeAlias, TypeVar

from bijux_rag.result.types import Err, ErrInfo, Ok, Result

from .plan import AsyncPlan

T = TypeVar("T")
U = TypeVar("U")
R = TypeVar("R")

AsyncGen: TypeAlias = Callable[[], AsyncIterator[Result[T, ErrInfo]]]


def async_gen_return(value: T) -> AsyncGen[T]:
    async def _gen() -> AsyncIterator[Result[T, ErrInfo]]:
        yield Ok(value)

    return lambda: _gen()


def async_gen_from_list(values: list[T]) -> AsyncGen[T]:
    async def _gen() -> AsyncIterator[Result[T, ErrInfo]]:
        for v in values:
            yield Ok(v)

    return lambda: _gen()


def async_gen_map(gen: AsyncGen[T], f: Callable[[T], U]) -> AsyncGen[U]:
    async def _mapped() -> AsyncIterator[Result[U, ErrInfo]]:
        async for item in gen():
            yield item.map(f)

    return lambda: _mapped()


def async_gen_map_action(gen: AsyncGen[T], f: Callable[[T], AsyncPlan[U]]) -> AsyncGen[U]:
    async def _mapped() -> AsyncIterator[Result[U, ErrInfo]]:
        async for item in gen():
            if isinstance(item, Err):
                yield Err(item.error)
            else:
                yield await f(item.value)()

    return lambda: _mapped()


def async_gen_and_then(gen: AsyncGen[T], f: Callable[[T], AsyncGen[U]]) -> AsyncGen[U]:
    async def _bound() -> AsyncIterator[Result[U, ErrInfo]]:
        async for item in gen():
            if isinstance(item, Err):
                yield Err(item.error)
                continue
            async for inner in f(item.value)():
                yield inner

    return lambda: _bound()


def async_gen_flat_map(gen: AsyncGen[T], f: Callable[[T], AsyncGen[U]]) -> AsyncGen[U]:
    return async_gen_and_then(gen, f)


def lift_async_item(fn: Callable[[T], Awaitable[Result[U, ErrInfo]]]) -> Callable[[T], AsyncGen[U]]:
    def lifted(x: T) -> AsyncGen[U]:
        async def _gen() -> AsyncIterator[Result[U, ErrInfo]]:
            yield await fn(x)

        return lambda: _gen()

    return lifted


def async_gen_using(
    cm_thunk: Callable[[], AbstractAsyncContextManager[R]],
    make_stream: Callable[[R], AsyncGen[T]],
) -> AsyncGen[T]:
    async def _using() -> AsyncIterator[Result[T, ErrInfo]]:
        async with cm_thunk() as resource:
            async for item in make_stream(resource)():
                yield item

    return lambda: _using()


def async_gen_gather(gens: list[AsyncGen[T]], *, max_buffer: int = 16) -> AsyncGen[T]:
    """Merge independent AsyncGen streams concurrently into one stream.

    The returned stream yields items from all sources in arrival order.
    Backpressure is enforced with a bounded queue of size `max_buffer`.
    """

    if max_buffer < 1:
        raise ValueError("max_buffer must be >= 1")

    async def _gathered() -> AsyncIterator[Result[T, ErrInfo]]:
        if not gens:
            return

        class _Done:
            __slots__ = ()

        done_marker = _Done()
        queue: asyncio.Queue[Result[T, ErrInfo] | _Done] = asyncio.Queue(maxsize=max_buffer)
        tasks: set[asyncio.Task[None]] = set()

        async def pump(gen: AsyncGen[T]) -> None:
            it = gen()
            try:
                async for item in it:
                    await queue.put(item)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - defensive
                await queue.put(Err(ErrInfo.from_exception(exc)))
            finally:
                aclose = getattr(it, "aclose", None)
                if aclose is not None:
                    await aclose()
                await queue.put(done_marker)

        for g in gens:
            tasks.add(asyncio.create_task(pump(g)))

        active = len(tasks)
        try:
            while active > 0:
                item = await queue.get()
                if isinstance(item, _Done):
                    active -= 1
                    continue
                yield item
        finally:
            for task in tasks:
                task.cancel()
            if tasks:
                _ = await asyncio.gather(*tasks, return_exceptions=True)

    return lambda: _gathered()


class Sleeper(Protocol):
    def now_ms(self) -> int: ...

    async def sleep_ms(self, ms: int) -> None: ...


@dataclass
class RealSleeper(Sleeper):
    def now_ms(self) -> int:
        return int(monotonic() * 1000.0)

    async def sleep_ms(self, ms: int) -> None:
        if ms < 0:
            raise ValueError("ms must be >= 0")
        await asyncio.sleep(ms / 1000.0)


@dataclass
class FakeSleeper(Sleeper):
    _now_ms: int = 0

    def now_ms(self) -> int:
        return self._now_ms

    async def sleep_ms(self, ms: int) -> None:
        if ms < 0:
            raise ValueError("ms must be >= 0")
        self._now_ms += ms
        await asyncio.sleep(0)

    def advance_ms(self, ms: int) -> None:
        if ms < 0:
            raise ValueError("ms must be >= 0")
        self._now_ms += ms


@dataclass(frozen=True)
class ChunkPolicy(Generic[T]):
    max_units: int = 128  # 0 = unbounded
    max_delay_ms: int = 500  # 0 = no time limit
    flush_on_err: bool = True
    size_fn: Callable[[T], int] = lambda _x: 1

    def __post_init__(self) -> None:
        if self.max_units < 0:
            raise ValueError("max_units must be >= 0")
        if self.max_delay_ms < 0:
            raise ValueError("max_delay_ms must be >= 0")


def async_gen_chunk(
    source: AsyncGen[T],
    policy: ChunkPolicy[T],
) -> Callable[[Sleeper], AsyncGen[list[T]]]:
    def make_chunked(sleeper: Sleeper) -> AsyncGen[list[T]]:
        async def _chunked() -> AsyncIterator[Result[list[T], ErrInfo]]:
            buf: list[T] = []
            buf_size = 0
            first_item_ts_ms: int | None = None
            it = source()

            try:
                try:
                    r = await anext(it)
                except StopAsyncIteration:
                    return

                while True:
                    if isinstance(r, Err):
                        if policy.flush_on_err and buf:
                            yield Ok(buf[:])
                            buf.clear()
                            buf_size = 0
                            first_item_ts_ms = None
                        yield Err(r.error)
                        try:
                            r = await anext(it)
                        except StopAsyncIteration:
                            return
                        continue

                    item = r.value
                    units = policy.size_fn(item)
                    if units < 0:
                        raise ValueError("size_fn must return >= 0")

                    time_flush = (
                        policy.max_delay_ms > 0
                        and first_item_ts_ms is not None
                        and sleeper.now_ms() - first_item_ts_ms >= policy.max_delay_ms
                    )
                    size_flush = policy.max_units > 0 and (buf_size + units > policy.max_units)

                    if (time_flush or size_flush) and buf:
                        yield Ok(buf[:])
                        buf.clear()
                        buf_size = 0
                        first_item_ts_ms = None

                    if policy.max_units > 0 and units > policy.max_units:
                        yield Ok([item])
                    else:
                        if not buf:
                            first_item_ts_ms = sleeper.now_ms()
                        buf.append(item)
                        buf_size += units

                    try:
                        r = await anext(it)
                    except StopAsyncIteration:
                        if buf:
                            yield Ok(buf[:])
                        return
            finally:
                aclose = getattr(it, "aclose", None)
                if aclose is not None:
                    await aclose()

        return lambda: _chunked()

    return make_chunked


__all__ = [
    # streams
    "AsyncGen",
    "async_gen_return",
    "async_gen_from_list",
    "async_gen_map",
    "async_gen_map_action",
    "async_gen_and_then",
    "async_gen_flat_map",
    "lift_async_item",
    "async_gen_using",
    "async_gen_gather",
    # chunking
    "Sleeper",
    "RealSleeper",
    "FakeSleeper",
    "ChunkPolicy",
    "async_gen_chunk",
]
