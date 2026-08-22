# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Typed policies and outcomes for interrupted Runtime recovery."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.inspection import RuntimeRunInspection


class RuntimeRecoveryError(RuntimeError):
    """An interrupted attempt cannot be recovered without ambiguity."""


class RecoveryStepDisposition(StrEnum):
    """How recovery handled one source step."""

    REUSED = "reused"
    EXECUTED = "executed"
    RECONCILED = "reconciled"


@dataclass(frozen=True, slots=True)
class RecoveredStep:
    """Recovery action and preserved output identities for one DAG node."""

    step_id: str
    operation: str
    disposition: RecoveryStepDisposition
    source_output_artifact_ids: tuple[ArtifactID, ...]
    recovery_output_artifact_ids: tuple[ArtifactID, ...]


@dataclass(frozen=True, slots=True)
class RuntimeRecoveryOutcome:
    """Superseding retry plus retained evidence and step-level recovery actions."""

    source: RuntimeRunInspection
    recovery: RuntimeRunInspection
    steps: tuple[RecoveredStep, ...]
    retained_source_artifact_ids: tuple[ArtifactID, ...]
    transition_artifact_ids: tuple[ArtifactID, ...]
    reused: bool


__all__ = [
    "RecoveredStep",
    "RecoveryStepDisposition",
    "RuntimeRecoveryError",
    "RuntimeRecoveryOutcome",
]
