# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import pytest

from bijux_vex.contracts.resources import ExecutionResources
from bijux_vex.contracts.tx import Tx
from bijux_vex.core.errors import InvariantError
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.types import ExecutionArtifact
from bijux_vex.domain.execution_artifacts import build
from bijux_vex.infra.adapters.memory.backend import memory_backend


def _artifact() -> ExecutionArtifact:
    return ExecutionArtifact(
        artifact_id="art-plan",
        corpus_fingerprint="corp",
        vector_fingerprint="vec",
        metric="l2",
        scoring_version="v1",
        build_params=(("p", "v"),),
        execution_contract=ExecutionContract.DETERMINISTIC,
    )


def test_make_build_plan_deterministic():
    art = _artifact()
    plan1 = build.make_build_plan(art)
    plan2 = build.make_build_plan(art)
    assert plan1.plan_fingerprint == plan2.plan_fingerprint


def test_materialize_requires_tx():
    art = _artifact()
    plan = build.make_build_plan(art)
    stores = memory_backend().stores
    with pytest.raises(InvariantError):
        build.materialize(plan, None, stores)


def test_materialize_writes_artifact():
    backend = memory_backend()
    art = _artifact()
    plan = build.make_build_plan(art)
    with backend.tx_factory() as tx:
        build.materialize(plan, tx, backend.stores)
    assert backend.stores.ledger.get_artifact(art.artifact_id) == art


def test_materialize_rejects_contract_mismatch():
    backend = memory_backend()
    existing = _artifact()
    with backend.tx_factory() as tx:
        backend.stores.ledger.put_artifact(tx, existing)
    new_art = ExecutionArtifact(
        artifact_id=existing.artifact_id,
        corpus_fingerprint=existing.corpus_fingerprint,
        vector_fingerprint=existing.vector_fingerprint,
        metric=existing.metric,
        scoring_version=existing.scoring_version,
        build_params=existing.build_params,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
    )
    plan = build.make_build_plan(new_art)
    with backend.tx_factory() as tx, pytest.raises(InvariantError):
        build.materialize(plan, tx, backend.stores)
