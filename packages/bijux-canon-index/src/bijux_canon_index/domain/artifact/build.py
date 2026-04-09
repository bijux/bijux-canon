# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Build helpers for domain logic."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_index.contracts.resources import ExecutionResources
from bijux_canon_index.contracts.tx import Tx
from bijux_canon_index.core.errors import InvariantError
from bijux_canon_index.core.identity.ids import fingerprint
from bijux_canon_index.core.types import ExecutionArtifact


@dataclass(frozen=True)
class BuildPlan:
    """Represents build plan."""

    artifact: ExecutionArtifact
    plan_fingerprint: str
    index_config_fingerprint: str


def make_build_plan(artifact: ExecutionArtifact) -> BuildPlan:
    """Handle make build plan."""
    return BuildPlan(
        artifact=artifact,
        plan_fingerprint=fingerprint(artifact),
        index_config_fingerprint=artifact.index_config_fingerprint
        or fingerprint(artifact.build_params),
    )


def materialize(plan: BuildPlan, tx: Tx | None, stores: ExecutionResources) -> None:
    """Handle materialize."""
    if tx is None or not isinstance(tx, Tx):
        raise InvariantError(message="materialize requires an active Tx")
    existing = stores.ledger.get_artifact(plan.artifact.artifact_id)
    if existing and existing.execution_contract is not plan.artifact.execution_contract:
        raise InvariantError(
            message="Cannot materialize artifact with different execution contract"
        )
    stores.ledger.put_artifact(tx, plan.artifact)
