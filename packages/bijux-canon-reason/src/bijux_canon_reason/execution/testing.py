# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Testing helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FakeRuntime:
    """Deterministic runtime placeholder used for tests (no hidden time/randomness)."""

    seed: int
