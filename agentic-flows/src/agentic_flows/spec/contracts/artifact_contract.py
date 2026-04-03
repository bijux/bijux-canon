# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/contracts/artifact_contract.py."""

from __future__ import annotations

from collections.abc import Iterable

from agentic_flows.spec.ontology import ArtifactType

_ALLOWED_PARENTS: dict[ArtifactType, set[ArtifactType]] = {
    ArtifactType.FLOW_MANIFEST: set(),
    ArtifactType.EXECUTION_PLAN: {ArtifactType.FLOW_MANIFEST},
    ArtifactType.RESOLVED_STEP: {
        ArtifactType.FLOW_MANIFEST,
        ArtifactType.EXECUTION_PLAN,
    },
    ArtifactType.AGENT_INVOCATION: {ArtifactType.RESOLVED_STEP},
    ArtifactType.RETRIEVAL_REQUEST: {ArtifactType.RESOLVED_STEP},
    ArtifactType.RETRIEVED_EVIDENCE: {ArtifactType.RETRIEVAL_REQUEST},
    ArtifactType.REASONING_STEP: {
        ArtifactType.RESOLVED_STEP,
        ArtifactType.RETRIEVED_EVIDENCE,
        ArtifactType.AGENT_INVOCATION,
    },
    ArtifactType.REASONING_CLAIM: {
        ArtifactType.REASONING_STEP,
        ArtifactType.RETRIEVED_EVIDENCE,
        ArtifactType.AGENT_INVOCATION,
    },
    ArtifactType.REASONING_BUNDLE: {
        ArtifactType.REASONING_STEP,
        ArtifactType.REASONING_CLAIM,
    },
    ArtifactType.VERIFICATION_RULE: {
        ArtifactType.FLOW_MANIFEST,
        ArtifactType.RESOLVED_STEP,
    },
    ArtifactType.VERIFICATION_RESULT: {
        ArtifactType.VERIFICATION_RULE,
        ArtifactType.REASONING_BUNDLE,
        ArtifactType.RETRIEVED_EVIDENCE,
        ArtifactType.AGENT_INVOCATION,
    },
    ArtifactType.EXECUTION_EVENT: {
        ArtifactType.RESOLVED_STEP,
        ArtifactType.VERIFICATION_RESULT,
    },
    ArtifactType.EXECUTION_TRACE: {
        ArtifactType.EXECUTION_PLAN,
        ArtifactType.EXECUTION_EVENT,
    },
    ArtifactType.EXECUTOR_STATE: {
        ArtifactType.AGENT_INVOCATION,
        ArtifactType.RESOLVED_STEP,
    },
}


def validate(parent_types: Iterable[ArtifactType], child_type: ArtifactType) -> None:
    """Validate artifact lineage; misuse breaks artifact contracts."""
    allowed = _ALLOWED_PARENTS.get(child_type)
    if allowed is None:
        raise ValueError(f"Unknown artifact type: {child_type}")

    parents = set(parent_types)
    if not allowed and parents:
        raise ValueError(f"{child_type.value} must not declare parent artifacts")

    invalid = parents.difference(allowed)
    if invalid:
        invalid_list = ", ".join(sorted(parent.value for parent in invalid))
        raise ValueError(f"{child_type.value} cannot depend on: {invalid_list}")


__all__ = ["validate"]
