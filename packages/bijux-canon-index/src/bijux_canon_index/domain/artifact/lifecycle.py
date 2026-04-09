# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Lifecycle helpers for domain logic."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from bijux_canon_index.core.errors import InvariantError
from bijux_canon_index.core.types import ExecutionArtifact


class IndexState(StrEnum):
    """Enumeration of index state."""
    UNBUILT = "unbuilt"
    BUILDING = "building"
    READY = "ready"
    INVALIDATED = "invalidated"


@dataclass(frozen=True)
class ExecutionArtifactState:
    """Represents execution artifact state."""
    artifact: ExecutionArtifact
    status: IndexState
    generation: int = 1


def build(artifact: ExecutionArtifact) -> ExecutionArtifactState:
    """Build artifact."""
    return ExecutionArtifactState(
        artifact=artifact, status=IndexState.READY, generation=1
    )


def invalidate(state: ExecutionArtifactState) -> ExecutionArtifactState:
    """Handle invalidate."""
    return replace(state, status=IndexState.INVALIDATED)


def begin_build(state: ExecutionArtifactState) -> ExecutionArtifactState:
    """Handle begin build."""
    if state.status is IndexState.BUILDING:
        return state
    if state.status is IndexState.INVALIDATED or state.status is IndexState.READY:
        return replace(state, status=IndexState.BUILDING)
    return replace(state, status=IndexState.BUILDING)


def rebuild(
    state: ExecutionArtifactState, artifact: ExecutionArtifact | None = None
) -> ExecutionArtifactState:
    """Handle rebuild."""
    target = artifact or state.artifact
    if target.artifact_id != state.artifact.artifact_id:
        raise InvariantError(message="Artifact ID cannot change during rebuild")
    if target.execution_contract is not state.artifact.execution_contract:
        raise InvariantError(message="Execution contract cannot change during rebuild")
    return ExecutionArtifactState(
        artifact=target, status=IndexState.READY, generation=state.generation + 1
    )
