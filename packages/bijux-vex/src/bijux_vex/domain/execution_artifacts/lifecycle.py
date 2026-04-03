# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from bijux_vex.core.errors import InvariantError
from bijux_vex.core.types import ExecutionArtifact


class IndexState(StrEnum):
    UNBUILT = "unbuilt"
    BUILDING = "building"
    READY = "ready"
    INVALIDATED = "invalidated"


@dataclass(frozen=True)
class ExecutionArtifactState:
    artifact: ExecutionArtifact
    status: IndexState
    generation: int = 1


def build(artifact: ExecutionArtifact) -> ExecutionArtifactState:
    return ExecutionArtifactState(
        artifact=artifact, status=IndexState.READY, generation=1
    )


def invalidate(state: ExecutionArtifactState) -> ExecutionArtifactState:
    return replace(state, status=IndexState.INVALIDATED)


def begin_build(state: ExecutionArtifactState) -> ExecutionArtifactState:
    if state.status is IndexState.BUILDING:
        return state
    if state.status is IndexState.INVALIDATED or state.status is IndexState.READY:
        return replace(state, status=IndexState.BUILDING)
    return replace(state, status=IndexState.BUILDING)


def rebuild(
    state: ExecutionArtifactState, artifact: ExecutionArtifact | None = None
) -> ExecutionArtifactState:
    target = artifact or state.artifact
    if target.artifact_id != state.artifact.artifact_id:
        raise InvariantError(message="Artifact ID cannot change during rebuild")
    if target.execution_contract is not state.artifact.execution_contract:
        raise InvariantError(message="Execution contract cannot change during rebuild")
    return ExecutionArtifactState(
        artifact=target, status=IndexState.READY, generation=state.generation + 1
    )
