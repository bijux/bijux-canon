# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass, field
import time

from bijux_canon_index.core.errors import BackendUnavailableError, BudgetExceededError
from bijux_canon_index.infra.logging import log_event


@dataclass
class NDExecutionGuard:
    rate_limit: int
    rate_window_seconds: int
    max_failures: int
    cooldown_seconds: int
    _rate_window_start: float = field(default_factory=time.time)
    _rate_count: int = 0
    _failures: int = 0
    _open_until: float = 0.0

    def enforce(self) -> None:
        now = time.time()
        if now < self._open_until:
            raise BackendUnavailableError(
                message="ND backend temporarily unavailable (circuit open)"
            )
        if self.rate_limit <= 0:
            return
        if now - self._rate_window_start > self.rate_window_seconds:
            self._rate_window_start = now
            self._rate_count = 0
        self._rate_count += 1
        if self._rate_count > self.rate_limit:
            raise BudgetExceededError(message="ND rate limit exceeded for this node")

    def record_success(self) -> None:
        self._failures = 0

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures < self.max_failures:
            return
        self._open_until = time.time() + self.cooldown_seconds
        log_event(
            "nd_circuit_open",
            failures=self._failures,
            cooldown_s=self.cooldown_seconds,
        )

    def health_report(self) -> dict[str, object]:
        return {
            "status": "open" if time.time() < self._open_until else "closed",
            "failures": self._failures,
            "open_until": self._open_until,
            "cooldown_s": self.cooldown_seconds,
        }


__all__ = ["NDExecutionGuard"]
