# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from collections import Counter
from collections.abc import AsyncIterator, Callable
from typing import TypeVar

from bijux_canon_ingest.domain.effects.asyncio import AsyncGen
from bijux_canon_ingest.result.types import Err, ErrInfo, Ok, Result

T = TypeVar("T")


def attempt_norm(trace: list[tuple[str, str]]) -> Counter[tuple[str, str]]:
    return Counter(trace)


def emission_norm(trace: list[tuple[str, str]]) -> Counter[tuple[str, str]]:
    return Counter(trace)


async def collect(gen: AsyncGen[T]) -> list[Result[T, ErrInfo]]:
    return [item async for item in gen()]


def async_gen_from_results(items: list[Result[T, ErrInfo]]) -> AsyncGen[T]:
    async def _gen() -> AsyncIterator[Result[T, ErrInfo]]:
        for item in items:
            yield item

    return lambda: _gen()


def key_for_result(item: Result[T, ErrInfo], key_ok: Callable[[T], str]) -> str:
    if isinstance(item, Ok):
        return key_ok(item.value)
    if isinstance(item, Err):
        if item.error.path:
            return str(item.error.path[0])
        return item.error.code
    raise AssertionError("unreachable")
