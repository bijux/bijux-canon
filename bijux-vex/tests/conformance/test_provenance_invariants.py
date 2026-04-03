# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_vex.boundaries.pydantic_edges.models import (
    ExecutionArtifactRequest,
    ExecutionRequestPayload,
    IngestRequest,
)
from bijux_vex.core.config import ExecutionConfig, VectorStoreConfig
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.types import ExecutionRequest
from bijux_vex.domain.provenance.lineage import explain_result
from bijux_vex.services._orchestrator import Orchestrator


def _setup_engine() -> Orchestrator:
    config = ExecutionConfig(vector_store=VectorStoreConfig(backend="memory"))
    engine = Orchestrator(config=config)
    engine.ingest(IngestRequest(documents=["a"], vectors=[[0.0, 0.0]]))
    engine.materialize(
        ExecutionArtifactRequest(execution_contract=ExecutionContract.DETERMINISTIC)
    )
    return engine


def test_deterministic_execution_has_stable_ids():
    engine = _setup_engine()
    req = ExecutionRequestPayload(
        vector=(0.0, 0.0),
        top_k=1,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
        execution_mode=ExecutionMode.STRICT,
    )
    first = engine.execute(req)
    second = engine.execute(req)
    assert first["execution_id"] == second["execution_id"]


def test_vector_store_usage_recorded_when_enabled():
    engine = _setup_engine()
    req = ExecutionRequestPayload(
        vector=(0.0, 0.0),
        top_k=1,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
        execution_mode=ExecutionMode.STRICT,
    )
    result = engine.execute(req)
    request = ExecutionRequest(
        request_id="probe",
        text=None,
        vector=(0.0, 0.0),
        top_k=1,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
        execution_mode=ExecutionMode.STRICT,
    )
    result_obj = next(
        iter(engine.stores.vectors.query(engine.default_artifact_id, request))
    )
    explanation = explain_result(result_obj, engine.stores)
    assert explanation["vector_store_backend"] == "memory"
