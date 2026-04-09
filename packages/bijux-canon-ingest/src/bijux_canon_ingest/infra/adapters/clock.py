# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Clock adapters for real and deterministic time sources."""

from __future__ import annotations

from datetime import datetime, timedelta

try:
    from datetime import UTC
except ImportError:  # pragma: no cover - interpreter compatibility for tooling
    UTC = UTC

from bijux_canon_ingest.domain.capabilities import Clock


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(UTC)


class MonotonicTestClock(Clock):
    def __init__(self, start: datetime | None = None) -> None:
        base = start or datetime.now(UTC)
        self._now = base.replace(tzinfo=UTC)

    def now(self) -> datetime:
        self._now += timedelta(microseconds=1)
        return self._now


__all__ = ["SystemClock", "MonotonicTestClock"]
