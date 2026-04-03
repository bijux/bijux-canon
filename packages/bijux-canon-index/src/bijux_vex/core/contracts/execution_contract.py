# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from enum import Enum


class ExecutionContract(Enum):
    DETERMINISTIC = "deterministic"
    NON_DETERMINISTIC = "non_deterministic"

    @property
    def maturity(self) -> str:
        # Explicit surface lock: deterministic is supported, ND is experimental
        return (
            "SUPPORTED" if self is ExecutionContract.DETERMINISTIC else "EXPERIMENTAL"
        )

    @property
    def support_level(self) -> str:
        """Actionable contract surface classification."""
        surface = {
            ExecutionContract.DETERMINISTIC: "SUPPORTED",
            ExecutionContract.NON_DETERMINISTIC: "STABLE_BOUNDED",
        }
        return surface[self]

    @classmethod
    def surface_matrix(cls) -> dict[str, str]:
        """Return support matrix for external validation."""
        return {c.value: c.support_level for c in cls}


__all__ = ["ExecutionContract"]
