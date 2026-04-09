# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Idempotency cache helpers for application workflows."""

from __future__ import annotations

from threading import Lock
from typing import Any


class IdempotencyCache:
    """Represents idempotency cache."""
    def __init__(self) -> None:
        """Initialize the instance."""
        self._lock = Lock()
        self._entries: dict[str, dict[str, Any]] = {}

    def load(self, key: str | None) -> dict[str, Any] | None:
        """Load key."""
        if not key:
            return None
        with self._lock:
            cached = self._entries.get(key)
            return None if cached is None else dict(cached)

    def store(self, key: str | None, result: dict[str, Any]) -> None:
        """Handle store."""
        if not key:
            return
        with self._lock:
            self._entries[key] = dict(result)


__all__ = ["IdempotencyCache"]
