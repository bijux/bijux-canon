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
from bijux_vex.core.types import ExecutionRequest
from bijux_vex.domain.provenance.lineage import explain_result
from bijux_vex.infra.adapters.vectorstore_registry import _redact_uri
from bijux_vex.services.execution_engine import VectorExecutionEngine


def test_redact_uri_masks_password() -> None:
    uri = "https://user:secret@host:6333/collection"
    redacted = _redact_uri(uri)
    assert redacted == "https://user:***@host:6333/collection"
    assert "secret" not in redacted


def test_provenance_does_not_leak_vector_store_secrets() -> None:
    engine = VectorExecutionEngine(
        config=ExecutionConfig(
            vector_store=VectorStoreConfig(
                backend="memory",
                uri="http://user:secret@localhost:6333/collection",
            )
        )
    )
    engine.ingest(IngestRequest(documents=["alpha"], vectors=[[0.0, 0.0]]))
    engine.materialize(
        ExecutionArtifactRequest(execution_contract=ExecutionContract.DETERMINISTIC)
    )
    result = engine.execute(
        ExecutionRequestPayload(
            request_text=None,
            vector=(0.0, 0.0),
            top_k=1,
            execution_contract=ExecutionContract.DETERMINISTIC,
            execution_intent=ExecutionIntent.EXACT_VALIDATION,
        )
    )
    vector_id = result["results"][0]
    obj = next(
        iter(
            engine.stores.vectors.query(
                engine.default_artifact_id,
                ExecutionRequest(
                    request_id="probe",
                    text=None,
                    vector=(0.0, 0.0),
                    top_k=1,
                    execution_contract=ExecutionContract.DETERMINISTIC,
                    execution_intent=ExecutionIntent.EXACT_VALIDATION,
                ),
            )
        )
    )
    provenance = explain_result(obj, engine.stores)
    uri = provenance["vector_store_uri_redacted"]
    assert uri is not None
    assert "secret" not in uri
