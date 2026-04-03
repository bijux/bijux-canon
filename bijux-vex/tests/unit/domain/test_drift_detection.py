# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.execution_intent import ExecutionIntent

import pytest

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    ExecutionRequest,
    Vector,
    ExecutionBudget,
)
from bijux_vex.domain.monitoring.divergence import detect_backend_drift
from bijux_vex.infra.adapters.memory.backend import memory_backend
from bijux_vex.core.errors import BackendDivergenceError


def _seed(backend, suffix: str, values=(0.0,)) -> ExecutionArtifact:
    with backend.tx_factory() as tx:
        doc = Document(document_id=f"d{suffix}", text="hi")
        chunk = Chunk(
            chunk_id=f"c{suffix}", document_id=doc.document_id, text=doc.text, ordinal=0
        )
        vec = Vector(
            vector_id=f"v{suffix}",
            chunk_id=chunk.chunk_id,
            values=values,
            dimension=len(values),
        )
        art = ExecutionArtifact(
            artifact_id="art",
            corpus_fingerprint="corp",
            vector_fingerprint="vec",
            metric="l2",
            scoring_version="v1",
            execution_contract=ExecutionContract.DETERMINISTIC,
        )
        backend.stores.vectors.put_document(tx, doc)
        backend.stores.vectors.put_chunk(tx, chunk)
        backend.stores.vectors.put_vector(tx, vec)
        backend.stores.ledger.put_artifact(tx, art)
    return art


def test_drift_detection_flags_divergence():
    a = memory_backend()
    b = memory_backend()
    _seed(a, "a", values=(0.0,))
    _seed(b, "b", values=(1.0,))
    req = ExecutionRequest(
        request_id="req",
        text=None,
        vector=(0.0,),
        top_k=1,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
    )
    with pytest.raises(BackendDivergenceError):
        detect_backend_drift("art", req, a.stores, b.stores)
