# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for spec/model/execution/execution_steps.py."""

from __future__ import annotations

from dataclasses import dataclass, field

from bijux_canon_runtime.spec.model.artifact.entropy_budget import EntropyBudget
from bijux_canon_runtime.spec.model.datasets.dataset_descriptor import DatasetDescriptor
from bijux_canon_runtime.spec.model.execution.non_deterministic_intent import (
    NonDeterministicIntent,
)
from bijux_canon_runtime.spec.model.execution.replay_envelope import ReplayEnvelope
from bijux_canon_runtime.spec.model.execution.resolved_step import ResolvedStep
from bijux_canon_runtime.spec.ontology import (
    DeterminismLevel,
    EntropyMagnitude,
    FlowState,
)
from bijux_canon_runtime.spec.ontology.ids import (
    EnvironmentFingerprint,
    FlowID,
    PlanHash,
    TenantID,
)
from bijux_canon_runtime.spec.ontology.public import ReplayAcceptability, ReplayMode


@dataclass(frozen=True)
class ExecutionSteps:
    """Planned execution steps; misuse breaks ordering invariants."""

    spec_version: str
    flow_id: FlowID
    tenant_id: TenantID
    flow_state: FlowState
    determinism_level: DeterminismLevel
    replay_acceptability: ReplayAcceptability
    entropy_budget: EntropyBudget
    replay_envelope: ReplayEnvelope
    dataset: DatasetDescriptor
    allow_deprecated_datasets: bool
    steps: tuple[ResolvedStep, ...]
    environment_fingerprint: EnvironmentFingerprint
    plan_hash: PlanHash
    resolution_metadata: tuple[tuple[str, str], ...]
    allowed_variance_class: EntropyMagnitude | None = None
    nondeterminism_intent: tuple[NonDeterministicIntent, ...] = field(
        default_factory=tuple
    )
    replay_mode: ReplayMode = ReplayMode.STRICT


__all__ = ["ExecutionSteps"]
