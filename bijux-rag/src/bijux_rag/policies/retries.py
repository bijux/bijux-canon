# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Pure retry engine with policies for Result-returning functions (end-of-Bijux RAG)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Generic, Iterable, Iterator, NamedTuple, TypeVar, cast

from bijux_rag.result import Err, Ok, Result

X = TypeVar("X")
Y = TypeVar("Y")
E = TypeVar("E")


@dataclass(frozen=True)
class RetryCtx(Generic[X, E]):
    item: X
    attempt: int
    error: E
    stage: str | None
    path: tuple[int, ...] | None
    policy_name: str


class RetryDecision(NamedTuple):
    retry: bool
    next_delay_ms: int | None


Classifier = Callable[[E], bool]
Policy = Callable[[RetryCtx[X, E]], RetryDecision]


def _annotate_err(
    e: E,
    *,
    attempt: int,
    max_attempts: int,
    policy: str,
    next_delay_ms: int | None = None,
) -> E:
    """Annotate error if it supports _replace and ctx (ErrInfo does)."""

    if hasattr(e, "_replace") and hasattr(e, "ctx"):
        e_any = cast(Any, e)
        ctx = dict(e_any.ctx or {})
        ctx.update({"attempt": attempt, "max_attempts": max_attempts, "policy": policy})
        if next_delay_ms is not None:
            ctx["next_delay_ms"] = next_delay_ms
        return cast(E, e_any._replace(ctx=MappingProxyType(ctx)))
    return e


def retry_map_iter(
    fn: Callable[[X], Result[Y, E]],
    xs: Iterable[X],
    *,
    classifier: Callable[[E], bool],
    policy: Callable[[RetryCtx[X, E]], RetryDecision],
    stage: str,
    key_path: Callable[[X], tuple[int, ...]] | None = None,
    max_attempts: int = 10,
    policy_name: str | None = None,
    inflight_cap: int = 64,
) -> Iterator[Result[Y, E]]:
    """Pure, fair, bounded retry over a Result-returning fn."""

    if max_attempts < 1:
        raise ValueError("max_attempts >= 1")
    if inflight_cap < 1:
        raise ValueError("inflight_cap >= 1")

    name = policy_name if policy_name is not None else str(getattr(policy, "__name__", "anonymous"))
    it = iter(xs)
    work: deque[tuple[X, int]] = deque()

    def prime() -> None:
        while len(work) < inflight_cap:
            try:
                work.append((next(it), 1))
            except StopIteration:
                break

    prime()

    while work:
        x, attempt = work.popleft()
        r = fn(x)

        if isinstance(r, Ok):
            yield r
            prime()
            continue

        e = r.error
        if not classifier(e):
            yield Err(_annotate_err(e, attempt=attempt, max_attempts=max_attempts, policy=name))
            prime()
            continue

        p = key_path(x) if key_path is not None else ()
        ctx = RetryCtx(item=x, attempt=attempt, error=e, stage=stage, path=p, policy_name=name)
        try:
            dec = policy(ctx)
        except Exception:  # noqa: BLE001 - policy is treated as user code
            dec = RetryDecision(retry=False, next_delay_ms=None)

        if dec.retry and attempt < max_attempts:
            work.append((x, attempt + 1))
        else:
            yield Err(
                _annotate_err(
                    e,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    policy=name,
                    next_delay_ms=dec.next_delay_ms,
                )
            )
        prime()


def fixed_policy(total_attempts: int) -> Policy[Any, Any]:
    def p(ctx: RetryCtx[Any, Any]) -> RetryDecision:
        return RetryDecision(retry=ctx.attempt < total_attempts, next_delay_ms=None)

    p.__name__ = f"fixed_policy[{total_attempts}]"
    return p


def exp_policy(total_attempts: int, base_ms: int, cap_ms: int) -> Policy[Any, Any]:
    def p(ctx: RetryCtx[Any, Any]) -> RetryDecision:
        delay = min(cap_ms, base_ms * (2 ** (ctx.attempt - 1)))
        return RetryDecision(retry=ctx.attempt < total_attempts, next_delay_ms=delay)

    p.__name__ = f"exp_policy[{total_attempts},{base_ms},{cap_ms}]"
    return p


def is_retriable_errinfo(e: Any) -> bool:
    code = getattr(e, "code", None)
    return code in {"RATE_LIMIT", "TIMEOUT", "CONN_RESET", "EMBED/UNAVAILABLE", "TRANSIENT"}


def restore_input_order(tagged: Iterable[tuple[int, Result[Y, E]]]) -> Iterator[Result[Y, E]]:
    """Restore input order from (idx, result) pairs (0-based consecutive indices)."""

    buffer: dict[int, Result[Y, E]] = {}
    expect = 0
    for idx, r in tagged:
        buffer[idx] = r
        while expect in buffer:
            yield buffer.pop(expect)
            expect += 1


__all__ = [
    "RetryCtx",
    "RetryDecision",
    "Classifier",
    "Policy",
    "retry_map_iter",
    "fixed_policy",
    "exp_policy",
    "is_retriable_errinfo",
    "restore_input_order",
]
