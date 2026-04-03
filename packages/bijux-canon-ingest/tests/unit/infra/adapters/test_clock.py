# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from bijux_canon_ingest.infra.adapters.clock import MonotonicTestClock, SystemClock


def test_system_clock_returns_aware_utc_datetime() -> None:
    now = SystemClock().now()
    assert now.tzinfo is not None
    assert now.utcoffset() is not None


def test_monotonic_test_clock_advances_on_each_read() -> None:
    clock = MonotonicTestClock()
    first = clock.now()
    second = clock.now()
    assert second > first
