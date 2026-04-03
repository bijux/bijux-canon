# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.types import ExecutionArtifact
from bijux_vex.infra.adapters.memory.backend import memory_backend


def test_abort_tx_does_not_emit_audit():
    backend = memory_backend()
    with backend.tx_factory() as tx:
        tx.abort()
    assert backend.stores.vectors.get_document("missing") is None
    assert len(backend.stores.vectors._state.audit_log) == 0  # type: ignore[attr-defined]


def test_abort_artifact_build_not_visible():
    backend = memory_backend()
    art = ExecutionArtifact(
        artifact_id="art-abort",
        corpus_fingerprint="corp",
        vector_fingerprint="vec",
        metric="l2",
        scoring_version="v1",
        build_params=(),
        execution_contract=ExecutionContract.DETERMINISTIC,
    )
    with backend.tx_factory() as tx:
        backend.stores.ledger.put_artifact(tx, art)
        tx.abort()
    assert backend.stores.ledger.get_artifact(art.artifact_id) is None
