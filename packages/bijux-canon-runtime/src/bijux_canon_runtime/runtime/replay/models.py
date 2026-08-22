# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Policies and outcomes for immutable Runtime replay."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.ontology.public import ReplayMode
from bijux_canon_runtime.runtime.inspection import RuntimeRunInspection


class RuntimeReplayError(RuntimeError):
    """A replay request cannot be executed under its declared policy."""


class ReplayNetworkPolicy(StrEnum):
    """Network authority available to a replay attempt."""

    DISABLED = "disabled"
    RECORDED_ONLY = "recorded-only"
    PERMITTED = "permitted"


@dataclass(frozen=True, slots=True)
class ReplayTolerance:
    """Explicit performance variance accepted independently of semantics."""

    max_duration_delta_ms: float = 1000.0
    max_duration_ratio: float = 5.0

    def __post_init__(self) -> None:
        if self.max_duration_delta_ms < 0 or self.max_duration_ratio < 1:
            raise ValueError("replay duration tolerances are invalid")


@dataclass(frozen=True, slots=True)
class RuntimeReplayPolicy:
    """Complete execution, provider, and comparison policy for one replay."""

    replay_mode: ReplayMode
    network_policy: ReplayNetworkPolicy
    provider_allowlist: tuple[str, ...] = ()
    tolerance: ReplayTolerance = field(default_factory=ReplayTolerance)

    def __post_init__(self) -> None:
        if any(not item.strip() for item in self.provider_allowlist):
            raise ValueError("replay provider allowlist contains an empty identity")
        if len(set(self.provider_allowlist)) != len(self.provider_allowlist):
            raise ValueError("replay provider allowlist contains duplicates")
        if (
            self.network_policy is not ReplayNetworkPolicy.PERMITTED
            and self.provider_allowlist
        ):
            raise ValueError("offline replay cannot declare live provider authority")


@dataclass(frozen=True, slots=True)
class ReplayStepIdentityComparison:
    """Output identity comparison for one exact DAG node."""

    step_id: str
    operation: str
    deterministic: bool
    source_output_artifact_ids: tuple[ArtifactID, ...]
    replay_output_artifact_ids: tuple[ArtifactID, ...]
    identities_equal: bool


@dataclass(frozen=True, slots=True)
class RuntimeReplayComparison:
    """Deterministic identity and declared timing-tolerance verdict."""

    dag_equal: bool
    exact_artifact_identities: bool
    deterministic_artifact_identities: bool
    source_duration_ms: float
    replay_duration_ms: float
    duration_delta_ms: float
    duration_ratio: float | None
    duration_within_tolerance: bool
    accepted: bool
    steps: tuple[ReplayStepIdentityComparison, ...]


@dataclass(frozen=True, slots=True)
class RuntimeReplayOutcome:
    """New linked attempt, persisted inspection, and immediate replay verdict."""

    source: RuntimeRunInspection
    replay: RuntimeRunInspection
    policy: RuntimeReplayPolicy
    comparison: RuntimeReplayComparison
    reused: bool
    transition_artifact_ids: tuple[ArtifactID, ...]


__all__ = [
    "ReplayNetworkPolicy",
    "ReplayStepIdentityComparison",
    "ReplayTolerance",
    "RuntimeReplayComparison",
    "RuntimeReplayError",
    "RuntimeReplayOutcome",
    "RuntimeReplayPolicy",
]
