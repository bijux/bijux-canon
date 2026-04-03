# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import pytest

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.errors import (
    BackendCapabilityError,
    InvariantError,
    NotFoundError,
    ValidationError,
)
from bijux_vex.core.types import ExecutionArtifact, ExecutionRequest, ExecutionBudget
from bijux_vex.contracts.resources import BackendCapabilities, ExecutionResources
from bijux_vex.domain.execution_requests.plan import build_execution_plan
from bijux_vex.infra.adapters.memory.backend import memory_backend


def _prepare_artifact(backend):
    art = ExecutionArtifact(
        artifact_id="art",
        corpus_fingerprint="corp",
        vector_fingerprint="vec",
        metric="l2",
        scoring_version="v1",
        build_params=(),
        execution_contract=ExecutionContract.DETERMINISTIC,
    )
    with backend.tx_factory() as tx:
        backend.stores.ledger.put_artifact(tx, art)
    return art


def test_missing_artifact_raises():
    backend = memory_backend()
    with pytest.raises(NotFoundError):
        backend.stores.vectors.query(
            "missing",
            ExecutionRequest(
                request_id="q",
                text=None,
                vector=(0.0,),
                top_k=1,
                execution_contract=ExecutionContract.DETERMINISTIC,
                execution_intent=ExecutionIntent.EXACT_VALIDATION,
            ),
        )


def test_empty_corpus_returns_empty():
    backend = memory_backend()
    art = _prepare_artifact(backend)
    art = ExecutionArtifact(
        artifact_id=art.artifact_id,
        corpus_fingerprint=art.corpus_fingerprint,
        vector_fingerprint=art.vector_fingerprint,
        metric=art.metric,
        scoring_version=art.scoring_version,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
    )
    results = list(
        backend.stores.vectors.query(
            art.artifact_id,
            ExecutionRequest(
                request_id="q",
                text=None,
                vector=(0.0,),
                top_k=1,
                execution_contract=ExecutionContract.DETERMINISTIC,
                execution_intent=ExecutionIntent.EXACT_VALIDATION,
            ),
        )
    )
    assert results == []


def test_malformed_query_vector_missing():
    backend = memory_backend()
    art = _prepare_artifact(backend)
    with pytest.raises(ValidationError):
        backend.stores.vectors.query(
            art.artifact_id,
            ExecutionRequest(
                request_id="q",
                text=None,
                vector=None,
                top_k=1,
                execution_contract=ExecutionContract.DETERMINISTIC,
                execution_intent=ExecutionIntent.EXACT_VALIDATION,
            ),
        )


def test_request_before_artifact_build_fails():
    backend = memory_backend()
    with pytest.raises(NotFoundError):
        backend.stores.vectors.query(
            "art-missing",
            ExecutionRequest(
                request_id="q",
                text=None,
                vector=(0.0,),
                top_k=1,
                execution_contract=ExecutionContract.DETERMINISTIC,
                execution_intent=ExecutionIntent.EXACT_VALIDATION,
            ),
        )


def test_contract_mismatch_rejected():
    backend = memory_backend()
    art = _prepare_artifact(backend)
    with pytest.raises(InvariantError):
        backend.stores.vectors.query(
            art.artifact_id,
            ExecutionRequest(
                request_id="q",
                text=None,
                vector=(0.0,),
                top_k=1,
                execution_contract=ExecutionContract.NON_DETERMINISTIC,
                execution_intent=ExecutionIntent.EXACT_VALIDATION,
                execution_mode=ExecutionMode.BOUNDED,
                execution_budget=ExecutionBudget(max_latency_ms=5, max_memory_mb=5),
            ),
        )


def test_backend_capability_mismatch_is_detected():
    backend = memory_backend()
    art = ExecutionArtifact(
        artifact_id="nd-art",
        corpus_fingerprint="corp",
        vector_fingerprint="vec",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
    )
    with backend.tx_factory() as tx:
        backend.stores.ledger.put_artifact(tx, art)
    nd_request = ExecutionRequest(
        request_id="q",
        text=None,
        vector=(0.0,),
        top_k=1,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
        execution_mode=ExecutionMode.BOUNDED,
        execution_budget=ExecutionBudget(max_ann_probes=1, max_error=1.0),
    )
    caps = BackendCapabilities(
        contracts={ExecutionContract.NON_DETERMINISTIC},
        deterministic_query=True,
        ann_support=False,
        supports_ann=False,
        metrics={"l2"},
        replayable=True,
        max_vector_size=None,
    )
    resources = ExecutionResources(
        name="memory",
        vectors=backend.stores.vectors,
        ledger=backend.stores.ledger,
        capabilities=caps,
    )
    with pytest.raises(BackendCapabilityError):
        build_execution_plan(
            art, nd_request, resources, randomness=None, ann_runner=None
        )
