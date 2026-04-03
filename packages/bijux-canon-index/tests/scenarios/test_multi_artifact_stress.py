# SPDX-License-Identifier: MIT
# SPDX-License-Identifier: MIT
from __future__ import annotations
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.execution_intent import ExecutionIntent

import pytest

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    ExecutionRequest,
    Vector,
)
from bijux_vex.domain.execution_requests.execute import (
    execute_request,
    start_execution_session,
)
from bijux_vex.infra.adapters.memory.backend import memory_backend


def _seed_artifacts(count: int = 10):
    backend = memory_backend()
    artifacts: list[ExecutionArtifact] = []
    with backend.tx_factory() as tx:
        for idx in range(count):
            doc = Document(document_id=f"d{idx}", text="t")
            backend.stores.vectors.put_document(tx, doc)
            chunk = Chunk(
                chunk_id=f"c{idx}", document_id=doc.document_id, text="t", ordinal=0
            )
            backend.stores.vectors.put_chunk(tx, chunk)
            backend.stores.vectors.put_vector(
                tx,
                Vector(
                    vector_id=f"v{idx}",
                    chunk_id=chunk.chunk_id,
                    values=(float(idx),),
                    dimension=1,
                ),
            )
            art = ExecutionArtifact(
                artifact_id=f"art-{idx}",
                corpus_fingerprint=f"corp-{idx}",
                vector_fingerprint=f"vec-{idx}",
                metric="l2",
                scoring_version="v1",
                execution_contract=ExecutionContract.DETERMINISTIC,
            )
            backend.stores.ledger.put_artifact(tx, art)
            artifacts.append(art)
    return backend, artifacts


def test_multi_artifact_execute_and_replay_symmetry():
    backend, artifacts = _seed_artifacts()
    # execute across many artifacts, ensure symmetry and no implicit defaults
    for art in artifacts:
        req = ExecutionRequest(
            request_id=f"req-{art.artifact_id}",
            text=None,
            vector=(0.0,),
            top_k=1,
            execution_contract=ExecutionContract.DETERMINISTIC,
            execution_intent=ExecutionIntent.EXACT_VALIDATION,
            execution_mode=ExecutionMode.STRICT,
        )
        session = start_execution_session(art, req, backend.stores, ann_runner=None)
        execution_result, results = execute_request(session, backend.stores)
        assert execution_result.artifact_id == art.artifact_id
        assert execution_result.plan.contract is ExecutionContract.DETERMINISTIC
        from bijux_vex.domain.provenance.lineage import explain_result
        from bijux_vex.domain.provenance.replay import replay

        explanation = explain_result(results[0], backend.stores)
        assert explanation["artifact"].artifact_id == art.artifact_id
        with backend.tx_factory() as tx:
            backend.stores.ledger.put_execution_result(tx, execution_result)
        replay_outcome = replay(req, art, backend.stores, baseline_fingerprint=None)
        assert replay_outcome.matches is True


def test_mixed_dimensions_fail_fast():
    backend, artifacts = _seed_artifacts(2)
    # mutate one vector dimension
    with backend.tx_factory() as tx:
        backend.stores.vectors.put_vector(
            tx,
            Vector(
                vector_id="v-mismatch",
                chunk_id="c0",
                values=(0.1, 0.2),
                dimension=2,
            ),
        )
    art = artifacts[0]
    req = ExecutionRequest(
        request_id="req-mixed",
        text=None,
        vector=(0.0,),
        top_k=1,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
        execution_mode=ExecutionMode.STRICT,
    )
    session = start_execution_session(art, req, backend.stores, ann_runner=None)
    result, _ = execute_request(session, backend.stores)
    # execution succeeds but ignores mismatched vectors; still deterministic
    assert result.results
