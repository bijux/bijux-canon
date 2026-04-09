# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Determinism contract helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeterminismReport:
    """Represents determinism report."""

    randomness_sources: tuple[str, ...]
    reproducibility_bounds: str
    expected_contract: str
    actual_contract: str
    notes: tuple[str, ...] = ()


__all__ = ["DeterminismReport"]
