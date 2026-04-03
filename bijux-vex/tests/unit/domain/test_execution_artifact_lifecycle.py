# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import pytest

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import InvariantError
from bijux_vex.core.types import ExecutionArtifact
from bijux_vex.domain.execution_artifacts import lifecycle


def _artifact() -> ExecutionArtifact:
    return ExecutionArtifact(
        artifact_id="art",
        corpus_fingerprint="corp",
        vector_fingerprint="vec",
        metric="l2",
        scoring_version="v1",
        build_params=(),
        execution_contract=ExecutionContract.DETERMINISTIC,
    )


def test_build_invalidate_rebuild_transitions():
    art = _artifact()
    state = lifecycle.build(art)
    assert state.status is lifecycle.IndexState.READY
    assert state.generation == 1

    invalid = lifecycle.invalidate(state)
    assert invalid.status is lifecycle.IndexState.INVALIDATED
    assert invalid.generation == 1

    rebuilt = lifecycle.rebuild(invalid)
    assert rebuilt.status is lifecycle.IndexState.READY
    assert rebuilt.generation == 2


def test_rebuild_rejects_contract_change():
    art = _artifact()
    state = lifecycle.build(art)
    different = ExecutionArtifact(
        artifact_id=art.artifact_id,
        corpus_fingerprint=art.corpus_fingerprint,
        vector_fingerprint=art.vector_fingerprint,
        metric=art.metric,
        scoring_version=art.scoring_version,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
    )
    with pytest.raises(InvariantError):
        lifecycle.rebuild(state, different)


def test_ledger_retention_limits(monkeypatch):
    art = _artifact()
    from bijux_vex.infra.adapters.memory.backend import (
        memory_backend,
        MemoryExecutionLedger,
    )

    backend = memory_backend()
    monkeypatch.setattr(MemoryExecutionLedger, "MAX_ARTIFACTS", 1)
    with backend.tx_factory() as tx:
        backend.stores.ledger.put_artifact(tx, art)
    new_art = ExecutionArtifact(
        artifact_id="art-2",
        corpus_fingerprint="corp",
        vector_fingerprint="vec",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.DETERMINISTIC,
    )
    with backend.tx_factory() as tx, pytest.raises(InvariantError):
        backend.stores.ledger.put_artifact(tx, new_art)
