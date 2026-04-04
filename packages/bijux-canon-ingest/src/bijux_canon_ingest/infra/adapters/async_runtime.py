# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Async runtime interpreter for shell-owned workflows."""

from __future__ import annotations

from typing import TypeVar

from bijux_canon_ingest.domain.effects.asyncio.plan import AsyncPlan
from bijux_canon_ingest.result.types import ErrInfo, Result

A = TypeVar("A")


async def perform_async(plan: AsyncPlan[A]) -> Result[A, ErrInfo]:
    """Interpret an `AsyncPlan` by awaiting its coroutine."""

    return await plan()


__all__ = ["perform_async"]
