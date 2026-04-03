# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from bijux_rag.domain.effects.io_plan import io_delay, perform
from bijux_rag.domain.effects.io_retry import RetryPolicy, retry_idempotent
from bijux_rag.result.types import Err, ErrInfo, Ok, Result


def test_retry_idempotent_retries_transient_errors(monkeypatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr("bijux_rag.domain.effects.io_retry.time.sleep", lambda s: sleeps.append(s))

    calls: list[int] = []

    def behaviour(_: int):
        def act() -> Result[Result[int, ErrInfo], ErrInfo]:
            calls.append(1)
            if len(calls) == 1:
                return Ok(Err(ErrInfo(code="RATE_LIMIT", msg="slow")))
            return Ok(Ok(7))

        return io_delay(act)

    policy = RetryPolicy(max_attempts=3, backoff_ms=lambda attempt: 50 * (attempt + 1))
    wrapped = retry_idempotent(policy)(behaviour)

    assert perform(wrapped(0)) == Ok(Ok(7))
    assert len(calls) == 2
    assert sleeps == [0.05]


def test_retry_idempotent_does_not_retry_non_transient() -> None:
    calls: list[int] = []

    def behaviour(_: int):
        def act() -> Result[Result[int, ErrInfo], ErrInfo]:
            calls.append(1)
            return Ok(Err(ErrInfo(code="BAD_INPUT", msg="nope")))

        return io_delay(act)

    policy = RetryPolicy(max_attempts=5, backoff_ms=lambda _: 1_000)
    wrapped = retry_idempotent(policy)(behaviour)

    assert perform(wrapped(0)) == Ok(Err(ErrInfo(code="BAD_INPUT", msg="nope")))
    assert len(calls) == 1
