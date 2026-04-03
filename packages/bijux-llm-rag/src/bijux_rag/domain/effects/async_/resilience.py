# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG: resilience for AsyncPlan – retry/timeout policies as pure data (domain)."""

from __future__ import annotations

import asyncio
import warnings
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from random import Random
from time import monotonic
from types import TracebackType
from typing import Protocol, TypeAlias, TypeVar

from bijux_rag.result.types import Err, ErrInfo, Ok, Result, make_errinfo

from .plan import AsyncPlan

T = TypeVar("T")
A = TypeVar("A")
B = TypeVar("B")

TimeoutCtx: TypeAlias = Callable[[float], AbstractAsyncContextManager[None]]


class Clock(Protocol):
    def now_s(self) -> float: ...


@dataclass
class SystemClock(Clock):
    def now_s(self) -> float:
        return monotonic()


@dataclass
class FakeClock(Clock):
    current_s: float = 0.0

    def now_s(self) -> float:
        return self.current_s

    def now_ms(self) -> int:
        return int(self.current_s * 1000.0)

    def advance_s(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("seconds must be >= 0")
        self.current_s += seconds


class FakeTimeout:
    def __init__(self, clock: FakeClock, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("seconds must be >= 0")
        self._clock = clock
        self._deadline = clock.now_s() + seconds

    async def __aenter__(self) -> None:  # pragma: no cover
        return None

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        if exc_type is not None:
            return False
        if self._clock.now_s() >= self._deadline:
            raise TimeoutError(f"Fake timeout after {self._deadline:.6f}s")
        return False


def make_fake_timeout_ctx(clock: FakeClock) -> TimeoutCtx:
    return lambda seconds: FakeTimeout(clock, seconds)


Sleep: TypeAlias = Callable[[float], Awaitable[None]]


@dataclass(frozen=True)
class ResilienceEnv:
    rng: Random
    sleep: Sleep
    clock: Clock

    @staticmethod
    def default() -> "ResilienceEnv":
        async def _sleep(seconds: float) -> None:
            await asyncio.sleep(seconds)

        return ResilienceEnv(rng=Random(), sleep=_sleep, clock=SystemClock())


def make_test_resilience_env(
    *,
    seed: int = 42,
    sleep: Sleep | None = None,
    clock: Clock | None = None,
) -> ResilienceEnv:
    async def _noop_sleep(_: float) -> None:
        await asyncio.sleep(0)

    return ResilienceEnv(rng=Random(seed), sleep=sleep or _noop_sleep, clock=clock or FakeClock())


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 1
    retriable_codes: frozenset[str] = frozenset({"TRANSIENT", "TIMEOUT", "RATE_LIMIT"})
    backoff_base_ms: int = 100
    max_backoff_ms: int = 10_000
    jitter_factor: float = 0.1
    idempotent: bool = True

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.backoff_base_ms < 0:
            raise ValueError("backoff_base_ms must be >= 0")
        if self.max_backoff_ms < 0:
            raise ValueError("max_backoff_ms must be >= 0")
        if not (0.0 <= self.jitter_factor <= 1.0):
            raise ValueError("jitter_factor must be in [0.0, 1.0]")


@dataclass(frozen=True)
class TimeoutPolicy:
    timeout_ms: int = 0

    def __post_init__(self) -> None:
        if self.timeout_ms <= 0:
            raise ValueError("timeout_ms must be > 0")


def async_with_resilience(
    step: AsyncPlan[T],
    retry: RetryPolicy,
    timeout: TimeoutPolicy | None = None,
    env: ResilienceEnv | None = None,
    *,
    timeout_ctx: TimeoutCtx | None = None,
) -> AsyncPlan[T]:
    if retry.max_attempts == 1 and timeout is None and env is None and timeout_ctx is None:
        return step

    async def _resilient() -> Result[T, ErrInfo]:
        local_env = env or ResilienceEnv.default()
        rng = local_env.rng
        last_err: ErrInfo | None = None
        warned_non_idempotent = False

        for attempt in range(1, retry.max_attempts + 1):
            try:
                if timeout is None:
                    res = await step()
                else:
                    seconds = timeout.timeout_ms / 1000.0
                    if timeout_ctx is not None:
                        async with timeout_ctx(seconds):
                            res = await step()
                    else:
                        res = await asyncio.wait_for(step(), timeout=seconds)

                if isinstance(res, Ok):
                    return res

                last_err = res.error
                if last_err.code not in retry.retriable_codes:
                    return res
            except TimeoutError:
                if timeout is None:
                    raise
                last_err = ErrInfo(code="TIMEOUT", msg=f"Timeout after {timeout.timeout_ms}ms")
                if "TIMEOUT" not in retry.retriable_codes:
                    return Err(last_err)
                if retry.max_attempts == 1:
                    return Err(last_err)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                last_err = ErrInfo.from_exception(exc)
                if last_err.code not in retry.retriable_codes:
                    return Err(last_err)
                if retry.max_attempts == 1:
                    return Err(last_err)

            if attempt > 1 and not retry.idempotent and not warned_non_idempotent:
                warnings.warn(
                    "Retrying a step marked non-idempotent — potential duplicate side-effects",
                    category=RuntimeWarning,
                    stacklevel=2,
                )
                warned_non_idempotent = True

            if attempt < retry.max_attempts:
                base_s = (
                    min(retry.backoff_base_ms * (2 ** (attempt - 1)), retry.max_backoff_ms) / 1000.0
                )
                jitter = base_s * retry.jitter_factor * (2.0 * rng.random() - 1.0)
                delay = max(0.0, base_s + jitter)
                await local_env.sleep(delay)

        meta: dict[str, object] = {"attempts": retry.max_attempts, "last_err": last_err}
        if not retry.idempotent:
            meta["warning"] = "retried non-idempotent step"
        path = last_err.path if last_err is not None else ()
        return Err(
            make_errinfo(
                code="MAX_RETRIES",
                msg=f"Failed after {retry.max_attempts} attempts",
                path=path,
                meta=meta,
            )
        )

    return lambda: _resilient()


def resilient_mapper(
    f: Callable[[A], AsyncPlan[B]],
    retry: RetryPolicy,
    timeout: TimeoutPolicy | None = None,
    env: ResilienceEnv | None = None,
    *,
    timeout_ctx: TimeoutCtx | None = None,
) -> Callable[[A], AsyncPlan[B]]:
    def wrapped(item: A) -> AsyncPlan[B]:
        return async_with_resilience(f(item), retry, timeout, env, timeout_ctx=timeout_ctx)

    return wrapped


__all__ = [
    "TimeoutCtx",
    "Clock",
    "SystemClock",
    "FakeClock",
    "FakeTimeout",
    "make_fake_timeout_ctx",
    "Sleep",
    "ResilienceEnv",
    "make_test_resilience_env",
    "RetryPolicy",
    "TimeoutPolicy",
    "async_with_resilience",
    "resilient_mapper",
]
