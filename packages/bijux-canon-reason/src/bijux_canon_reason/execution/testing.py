# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Testing helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeterministicTestRuntime:
    """Minimal deterministic test value with no supported runtime behavior."""

    seed: int
