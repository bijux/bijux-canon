# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_canon_index.application.orchestration.idempotency_cache import (
    IdempotencyCache,
)


def test_idempotency_cache_returns_copies() -> None:
    cache = IdempotencyCache()

    cache.store("abc", {"ingested": 1})
    first = cache.load("abc")
    second = cache.load("abc")

    assert first == {"ingested": 1}
    assert second == {"ingested": 1}
    assert first is not second
