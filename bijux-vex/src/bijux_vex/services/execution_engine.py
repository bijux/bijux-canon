# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_vex.core.contracts.execution_abi import assert_execution_abi
from bijux_vex.services._orchestrator import Orchestrator


class VectorExecutionEngine(Orchestrator):
    """Thin wrapper aliasing Orchestrator to the public engine name."""

    # Explicit pass-throughs to keep public surface stable and testable
    def list_artifacts(
        self, *, limit: int | None = None, offset: int = 0
    ) -> dict[str, object]:
        return super().list_artifacts(limit=limit, offset=offset)

    def capabilities(self) -> dict[str, object]:
        return super().capabilities()


assert_execution_abi()

__all__ = ["VectorExecutionEngine"]
