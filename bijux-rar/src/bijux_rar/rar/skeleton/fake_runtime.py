# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FakeRuntime:
    """Deterministic runtime placeholder used for tests (no hidden time/randomness)."""

    seed: int
