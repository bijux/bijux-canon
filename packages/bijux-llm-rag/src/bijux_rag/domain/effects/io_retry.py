# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG: retry wrapper for idempotent IOPlan behaviours (sync version).

This is distinct from `bijux_rag.policies.retries`:
- `policies.retries` is a pure retry engine for `Result`-returning functions over iterables.
- `io_retry` wraps *effectful* `IOPlan[Result[T, ErrInfo]]` behaviours.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from bijux_rag.result.types import Err, ErrInfo, Ok, Result

from .io_plan import IOPlan, io_bind, io_delay, io_pure

A = TypeVar("A")
T = TypeVar("T")


def is_transient(err: ErrInfo) -> bool:
    """Domain-specific transient error detection."""

    return err.code in {"NETWORK_TIMEOUT", "RATE_LIMIT", "SERVICE_UNAVAILABLE"}


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int
    backoff_ms: Callable[[int], int]


def retry_idempotent(
    policy: RetryPolicy,
) -> Callable[
    [Callable[[A], IOPlan[Result[T, ErrInfo]]]], Callable[[A], IOPlan[Result[T, ErrInfo]]]
]:
    """Retry wrapper for idempotent behaviours only (synchronous/backoff variant)."""

    def lift(
        behaviour: Callable[[A], IOPlan[Result[T, ErrInfo]]],
    ) -> Callable[[A], IOPlan[Result[T, ErrInfo]]]:
        def run(a: A) -> IOPlan[Result[T, ErrInfo]]:
            def step(attempt: int) -> IOPlan[Result[T, ErrInfo]]:
                if attempt >= policy.max_attempts:
                    return io_pure(
                        Err(ErrInfo(code="MAX_RETRY", msg=f"Failed after {attempt} attempts"))
                    )

                plan = behaviour(a)

                def handle(r: Result[T, ErrInfo]) -> IOPlan[Result[T, ErrInfo]]:
                    if isinstance(r, Ok):
                        return io_pure(r)
                    if not is_transient(r.error):
                        return io_pure(r)
                    delay_ms = policy.backoff_ms(attempt)
                    return io_bind(io_delay(lambda: _sleep(delay_ms)), lambda _: step(attempt + 1))

                return io_bind(plan, handle)

            return step(0)

        return run

    return lift


def _sleep(delay_ms: int) -> Result[None, ErrInfo]:
    time.sleep(delay_ms / 1000.0)
    return Ok(None)


__all__ = ["RetryPolicy", "is_transient", "retry_idempotent"]
