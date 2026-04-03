# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for model/flow_manifest.py."""

from __future__ import annotations

from dataclasses import dataclass, field

from bijux_canon_runtime.model.artifact.entropy_budget import EntropyBudget
from bijux_canon_runtime.model.datasets.dataset_descriptor import DatasetDescriptor
from bijux_canon_runtime.model.execution.non_deterministic_intent import (
    NonDeterministicIntent,
)
from bijux_canon_runtime.model.execution.replay_envelope import ReplayEnvelope
from bijux_canon_runtime.spec.ontology import (
    DeterminismLevel,
    EntropyMagnitude,
    FlowState,
)
from bijux_canon_runtime.spec.ontology.ids import (
    AgentID,
    ContractID,
    FlowID,
    GateID,
    TenantID,
)
from bijux_canon_runtime.spec.ontology.public import ReplayAcceptability, ReplayMode


# NOTE: This manifest defines structure only.
# Semantic validity is enforced elsewhere.
@dataclass(frozen=True)
class FlowManifest:
    """Flow manifest contract; misuse breaks plan validity."""

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
    agents: tuple[AgentID, ...]
    dependencies: tuple[str, ...]
    retrieval_contracts: tuple[ContractID, ...]
    verification_gates: tuple[GateID, ...]
    allowed_variance_class: EntropyMagnitude | None = None
    nondeterminism_intent: tuple[NonDeterministicIntent, ...] = field(
        default_factory=tuple
    )
    replay_mode: ReplayMode = ReplayMode.STRICT


__all__ = ["FlowManifest"]
