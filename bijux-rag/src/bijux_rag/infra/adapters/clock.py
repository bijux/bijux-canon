# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG infra: clocks (real + deterministic test)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bijux_rag.domain.capabilities import Clock


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class MonotonicTestClock(Clock):
    def __init__(self, start: datetime | None = None) -> None:
        base = start or datetime.now(timezone.utc)
        self._now = base.replace(tzinfo=timezone.utc)

    def now(self) -> datetime:
        self._now += timedelta(microseconds=1)
        return self._now


__all__ = ["SystemClock", "MonotonicTestClock"]
