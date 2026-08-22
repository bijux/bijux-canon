# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Immutable Runtime replay policy, execution, and comparison."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bijux_canon_runtime.runtime.replay.models import (
    ReplayNetworkPolicy,
    ReplayStepIdentityComparison,
    ReplayTolerance,
    RuntimeReplayComparison,
    RuntimeReplayError,
    RuntimeReplayOutcome,
    RuntimeReplayPolicy,
)
from bijux_canon_runtime.runtime.replay.plan_reconstruction import (
    ReconstructedReplayPlan,
    reconstruct_linked_plan,
    reconstruct_replay_plan,
)

if TYPE_CHECKING:
    from bijux_canon_runtime.runtime.replay.service import RuntimeReplayService

__all__ = [
    "ReconstructedReplayPlan",
    "ReplayNetworkPolicy",
    "ReplayStepIdentityComparison",
    "ReplayTolerance",
    "RuntimeReplayComparison",
    "RuntimeReplayError",
    "RuntimeReplayOutcome",
    "RuntimeReplayPolicy",
    "RuntimeReplayService",
    "reconstruct_linked_plan",
    "reconstruct_replay_plan",
]


def __getattr__(name: str) -> Any:
    """Load the execution service without coupling replay policy imports to execution."""
    if name == "RuntimeReplayService":
        from bijux_canon_runtime.runtime.replay.service import RuntimeReplayService

        globals()[name] = RuntimeReplayService
        return RuntimeReplayService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Include the lazy execution service in interactive discovery."""
    return sorted(set(globals()) | set(__all__))
