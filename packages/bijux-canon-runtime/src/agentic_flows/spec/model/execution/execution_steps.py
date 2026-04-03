# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/model/execution/execution_steps.py."""

from __future__ import annotations

from dataclasses import dataclass, field

from agentic_flows.spec.model.artifact.entropy_budget import EntropyBudget
from agentic_flows.spec.model.datasets.dataset_descriptor import DatasetDescriptor
from agentic_flows.spec.model.execution.non_deterministic_intent import (
    NonDeterministicIntent,
)
from agentic_flows.spec.model.execution.replay_envelope import ReplayEnvelope
from agentic_flows.spec.model.execution.resolved_step import ResolvedStep
from agentic_flows.spec.ontology import (
    DeterminismLevel,
    EntropyMagnitude,
    FlowState,
)
from agentic_flows.spec.ontology.ids import (
    EnvironmentFingerprint,
    FlowID,
    PlanHash,
    TenantID,
)
from agentic_flows.spec.ontology.public import ReplayAcceptability, ReplayMode


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
