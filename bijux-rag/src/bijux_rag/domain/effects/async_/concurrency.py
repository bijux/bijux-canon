# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG: AsyncGen concurrency controls (end-of-Bijux RAG).

This module groups correlated "flow control" primitives:
- bounded concurrency / backpressure (`async_gen_bounded_map`)
- rate limiting (`async_gen_rate_limited`)
- weighted fairness fan-in (`async_gen_fair_merge`)
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TypeVar

from bijux_rag.result.types import Err, ErrInfo, Result

from .plan import AsyncPlan
from .resilience import ResilienceEnv
from .stream import AsyncGen

T = TypeVar("T")
U = TypeVar("U")


@dataclass(frozen=True)
class BackpressurePolicy:
    max_concurrent: int = 8
    ordered: bool = True

    def __post_init__(self) -> None:
        if self.max_concurrent < 1:
            raise ValueError("max_concurrent must be >= 1")


def async_gen_bounded_map(
    source: AsyncGen[T],
    f: Callable[[T], AsyncPlan[U]],
    policy: BackpressurePolicy,
) -> AsyncGen[U]:
    """Apply `f` over an AsyncGen with bounded concurrency.

    - `ordered=True`: preserves input order with a bounded sliding window.
    - `ordered=False`: yields in completion order (still bounded memory).

    Errors from `source` are yielded as-is and do not call `f`.
    """

    max_concurrent = policy.max_concurrent

    if not policy.ordered:

        async def _unordered() -> AsyncIterator[Result[U, ErrInfo]]:
            sem = asyncio.Semaphore(max_concurrent)
            pending: set[asyncio.Task[Result[U, ErrInfo]]] = set()
            it = source()

            async def worker(value: T) -> Result[U, ErrInfo]:
                try:
                    return await f(value)()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # pragma: no cover - defensive
                    return Err(ErrInfo.from_exception(exc))
                finally:
                    sem.release()

            try:
                async for item in it:
                    if isinstance(item, Err):
                        yield Err(item.error)
                        continue

                    await sem.acquire()
                    pending.add(asyncio.create_task(worker(item.value)))

                    if len(pending) >= max_concurrent:
                        done, pending = await asyncio.wait(
                            pending, return_when=asyncio.FIRST_COMPLETED
                        )
                        for task in done:
                            yield task.result()

                while pending:
                    done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                    for task in done:
                        yield task.result()
            finally:
                for task in pending:
                    task.cancel()
                if pending:
                    _ = await asyncio.gather(*pending, return_exceptions=True)
                aclose = getattr(it, "aclose", None)
                if aclose is not None:
                    await aclose()

        return lambda: _unordered()

    async def _ordered() -> AsyncIterator[Result[U, ErrInfo]]:
        sem = asyncio.Semaphore(max_concurrent)
        pending: set[asyncio.Task[tuple[int, Result[U, ErrInfo]]]] = set()
        buffer: dict[int, Result[U, ErrInfo]] = {}
        next_expected = 0
        idx = 0
        it = source()

        async def worker(i: int, value: T) -> tuple[int, Result[U, ErrInfo]]:
            try:
                res = await f(value)()
                return i, res
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - defensive
                return i, Err(ErrInfo.from_exception(exc))
            finally:
                sem.release()

        try:
            async for item in it:
                while idx - next_expected >= max_concurrent:
                    if not pending:
                        raise RuntimeError("Backpressure window violation")
                    done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                    for task in done:
                        pending.remove(task)
                        i, res = task.result()
                        buffer[i] = res
                    while next_expected in buffer:
                        yield buffer.pop(next_expected)
                        next_expected += 1

                if isinstance(item, Err):
                    buffer[idx] = Err(item.error)
                else:
                    await sem.acquire()
                    pending.add(asyncio.create_task(worker(idx, item.value)))

                while next_expected in buffer:
                    yield buffer.pop(next_expected)
                    next_expected += 1

                idx += 1

            while pending:
                done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    pending.remove(task)
                    i, res = task.result()
                    buffer[i] = res

            while next_expected in buffer:
                yield buffer.pop(next_expected)
                next_expected += 1
        finally:
            for task in pending:
                task.cancel()
            if pending:
                _ = await asyncio.gather(*pending, return_exceptions=True)
            aclose = getattr(it, "aclose", None)
            if aclose is not None:
                await aclose()

    return lambda: _ordered()


@dataclass(frozen=True)
class RateLimitPolicy:
    tokens_per_second: float = 10.0
    burst_tokens: int = 10

    def __post_init__(self) -> None:
        if self.tokens_per_second <= 0:
            raise ValueError("tokens_per_second must be > 0")
        if self.burst_tokens < 1:
            raise ValueError("burst_tokens must be >= 1")


def async_gen_rate_limited(
    stream: AsyncGen[T],
    policy: RateLimitPolicy,
    *,
    env: ResilienceEnv | None = None,
) -> AsyncGen[T]:
    local_env = env or ResilienceEnv.default()

    async def _limited() -> AsyncIterator[Result[T, ErrInfo]]:
        tokens = float(policy.burst_tokens)
        last_refill_s = local_env.clock.now_s()

        async for item in stream():
            now = local_env.clock.now_s()
            elapsed = now - last_refill_s
            tokens = min(float(policy.burst_tokens), tokens + elapsed * policy.tokens_per_second)
            last_refill_s = now

            if tokens < 1.0:
                await local_env.sleep((1.0 - tokens) / policy.tokens_per_second)
                now = local_env.clock.now_s()
                elapsed = now - last_refill_s
                tokens = min(
                    float(policy.burst_tokens), tokens + elapsed * policy.tokens_per_second
                )
                last_refill_s = now

            tokens -= 1.0
            yield item

    return lambda: _limited()


@dataclass(frozen=True)
class FairnessPolicy:
    weights: Mapping[int, int] = field(default_factory=dict)
    max_buffer_per_stream: int = 16

    def __post_init__(self) -> None:
        if self.max_buffer_per_stream < 1:
            raise ValueError("max_buffer_per_stream must be >= 1")
        for k, v in self.weights.items():
            if k < 0:
                raise ValueError("weights keys must be >= 0")
            if v < 1:
                raise ValueError("weights values must be >= 1")


def async_gen_fair_merge(
    streams: Sequence[AsyncGen[T]],
    policy: FairnessPolicy | None = None,
) -> AsyncGen[T]:
    policy = policy or FairnessPolicy()
    weights = [policy.weights.get(i, 1) for i in range(len(streams))]

    async def _fair() -> AsyncIterator[Result[T, ErrInfo]]:
        iters = [s() for s in streams]
        buffers: list[deque[Result[T, ErrInfo]]] = [deque() for _ in streams]
        active = [True] * len(streams)
        emitted = [0] * len(streams)

        async def refill(i: int) -> None:
            while active[i] and len(buffers[i]) < policy.max_buffer_per_stream:
                try:
                    buffers[i].append(await iters[i].__anext__())
                except StopAsyncIteration:
                    active[i] = False
                    break
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # pragma: no cover - defensive
                    buffers[i].append(Err(ErrInfo.from_exception(exc)))
                    break

        try:
            for i in range(len(streams)):
                await refill(i)

            while any(active) or any(buffers):
                selected = -1
                best_ratio = float("inf")
                for i in range(len(streams)):
                    if buffers[i]:
                        ratio = emitted[i] / weights[i]
                        if ratio < best_ratio or (
                            ratio == best_ratio and (selected == -1 or i < selected)
                        ):
                            best_ratio = ratio
                            selected = i

                if selected != -1:
                    yield buffers[selected].popleft()
                    emitted[selected] += 1
                    await refill(selected)
                    continue

                progress = False
                for i in range(len(streams)):
                    if active[i] and len(buffers[i]) < policy.max_buffer_per_stream:
                        before = len(buffers[i])
                        await refill(i)
                        progress = progress or (len(buffers[i]) > before)

                if not progress:
                    await asyncio.sleep(0)
        finally:
            for it in iters:
                aclose = getattr(it, "aclose", None)
                if aclose is not None:
                    await aclose()

    return lambda: _fair()


__all__ = [
    "BackpressurePolicy",
    "async_gen_bounded_map",
    "RateLimitPolicy",
    "async_gen_rate_limited",
    "FairnessPolicy",
    "async_gen_fair_merge",
]
