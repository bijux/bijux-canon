# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeterminismReport:
    randomness_sources: tuple[str, ...]
    reproducibility_bounds: str
    expected_contract: str
    actual_contract: str
    notes: tuple[str, ...] = ()


__all__ = ["DeterminismReport"]
