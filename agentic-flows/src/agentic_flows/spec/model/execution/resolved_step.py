# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/model/execution/resolved_step.py."""

from __future__ import annotations

from dataclasses import dataclass, field

from agentic_flows.spec.model.artifact.entropy_budget import EntropyBudget
from agentic_flows.spec.model.datasets.retrieval_request import RetrievalRequest
from agentic_flows.spec.model.execution.non_deterministic_intent import (
    NonDeterministicIntent,
)
from agentic_flows.spec.model.identifiers.agent_invocation import AgentInvocation
from agentic_flows.spec.ontology import (
    DeterminismLevel,
    EntropyMagnitude,
    StepType,
)
from agentic_flows.spec.ontology.ids import AgentID, ArtifactID, InputsFingerprint


@dataclass(frozen=True)
class ResolvedStep:
    """Resolved step; misuse breaks execution ordering."""

    spec_version: str
    step_index: int
    step_type: StepType
    determinism_level: DeterminismLevel
    agent_id: AgentID
    inputs_fingerprint: InputsFingerprint
    declared_dependencies: tuple[AgentID, ...]
    expected_artifacts: tuple[ArtifactID, ...]
    agent_invocation: AgentInvocation
    retrieval_request: RetrievalRequest | None
    declared_entropy_budget: EntropyBudget | None = None
    allowed_variance_class: EntropyMagnitude | None = None
    nondeterminism_intent: tuple[NonDeterministicIntent, ...] = field(
        default_factory=tuple
    )


__all__ = ["ResolvedStep"]
