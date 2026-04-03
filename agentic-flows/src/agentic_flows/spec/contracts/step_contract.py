# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/contracts/step_contract.py."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from agentic_flows.spec.model.artifact.artifact import Artifact
from agentic_flows.spec.model.artifact.retrieved_evidence import RetrievedEvidence
from agentic_flows.spec.ontology import (
    ArtifactScope,
    ArtifactType,
    StepType,
)


@dataclass(frozen=True)
class StepContract:
    """Step contract; misuse breaks step invariants."""

    required_evidence: bool
    allowed_artifact_types: tuple[ArtifactType, ...]
    forbidden_scopes: tuple[ArtifactScope, ...]


_CONTRACTS: dict[StepType, StepContract] = {
    StepType.AGENT: StepContract(
        required_evidence=False,
        allowed_artifact_types=(
            ArtifactType.AGENT_INVOCATION,
            ArtifactType.EXECUTOR_STATE,
        ),
        forbidden_scopes=(),
    ),
    StepType.RETRIEVAL: StepContract(
        required_evidence=True,
        allowed_artifact_types=(),
        forbidden_scopes=(),
    ),
    StepType.REASONING: StepContract(
        required_evidence=False,
        allowed_artifact_types=(ArtifactType.REASONING_BUNDLE,),
        forbidden_scopes=(ArtifactScope.WORKING, ArtifactScope.EPHEMERAL),
    ),
    StepType.VERIFICATION: StepContract(
        required_evidence=False,
        allowed_artifact_types=(),
        forbidden_scopes=(),
    ),
}


def validate_outputs(
    step_type: StepType,
    artifacts: Iterable[Artifact],
    evidence: Iterable[RetrievedEvidence],
) -> None:
    """Validate step outputs; misuse breaks step guarantees."""
    contract = _CONTRACTS[step_type]
    artifact_list = list(artifacts)
    evidence_list = list(evidence)

    if contract.required_evidence and not evidence_list:
        raise ValueError(f"{step_type.value} requires evidence")

    if contract.allowed_artifact_types:
        invalid = [
            artifact
            for artifact in artifact_list
            if artifact.artifact_type not in contract.allowed_artifact_types
        ]
        if invalid:
            raise ValueError(
                f"{step_type.value} produced invalid artifact types: "
                f"{', '.join(item.artifact_type.value for item in invalid)}"
            )
    elif artifact_list:
        raise ValueError(f"{step_type.value} must not produce artifacts")

    forbidden = set(contract.forbidden_scopes)
    if forbidden and any(item.scope in forbidden for item in artifact_list):
        raise ValueError(f"{step_type.value} produced forbidden artifact scopes")


__all__ = ["StepContract", "validate_outputs"]
