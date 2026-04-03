# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for model/execution/resolved_step.py."""

from __future__ import annotations

from dataclasses import dataclass, field

from bijux_canon_runtime.model.artifact.entropy_budget import EntropyBudget
from bijux_canon_runtime.model.datasets.retrieval_request import RetrievalRequest
from bijux_canon_runtime.model.execution.non_deterministic_intent import (
    NonDeterministicIntent,
)
from bijux_canon_runtime.model.identifiers.agent_invocation import AgentInvocation
from bijux_canon_runtime.ontology import (
    DeterminismLevel,
    EntropyMagnitude,
    StepType,
)
from bijux_canon_runtime.ontology.ids import AgentID, ArtifactID, InputsFingerprint


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
