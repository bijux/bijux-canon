# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass

from bijux_vex.contracts.resources import ExecutionResources
from bijux_vex.contracts.tx import Tx
from bijux_vex.core.errors import InvariantError
from bijux_vex.core.identity.ids import fingerprint
from bijux_vex.core.types import ExecutionArtifact


@dataclass(frozen=True)
class BuildPlan:
    artifact: ExecutionArtifact
    plan_fingerprint: str
    index_config_fingerprint: str


def make_build_plan(artifact: ExecutionArtifact) -> BuildPlan:
    return BuildPlan(
        artifact=artifact,
        plan_fingerprint=fingerprint(artifact),
        index_config_fingerprint=artifact.index_config_fingerprint
        or fingerprint(artifact.build_params),
    )


def materialize(plan: BuildPlan, tx: Tx | None, stores: ExecutionResources) -> None:
    if tx is None or not isinstance(tx, Tx):
        raise InvariantError(message="materialize requires an active Tx")
    existing = stores.ledger.get_artifact(plan.artifact.artifact_id)
    if existing and existing.execution_contract is not plan.artifact.execution_contract:
        raise InvariantError(
            message="Cannot materialize artifact with different execution contract"
        )
    stores.ledger.put_artifact(tx, plan.artifact)
