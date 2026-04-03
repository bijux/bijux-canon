# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_vex.contracts.resources import ExecutionResources
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import NotFoundError
from bijux_vex.core.identity.fingerprints import determinism_fingerprint
from bijux_vex.core.types import Result


def explain_result(result: Result, stores: ExecutionResources) -> dict[str, object]:
    document = stores.vectors.get_document(result.document_id)
    if document is None:
        raise NotFoundError(
            message=f"Document {result.document_id} missing for explanation"
        )
    chunk = stores.vectors.get_chunk(result.chunk_id)
    if chunk is None:
        raise NotFoundError(message=f"Chunk {result.chunk_id} missing for explanation")
    vector = stores.vectors.get_vector(result.vector_id)
    if vector is None:
        raise NotFoundError(
            message=f"Vector {result.vector_id} missing for explanation"
        )
    artifact = stores.ledger.get_artifact(result.artifact_id)
    if artifact is None:
        raise NotFoundError(
            message=f"Execution artifact {result.artifact_id} missing for explanation"
        )

    nondeterministic_sources: tuple[str, ...] = ()
    lossy_dimensions: tuple[str, ...] = ()
    execution_contract_status = "stable"
    if artifact.execution_contract is ExecutionContract.NON_DETERMINISTIC:
        nondeterministic_sources = ("approximate_execution",)
        lossy_dimensions = ("ranking",)
        execution_contract_status = "experimental"
    vector_store_metadata = getattr(stores.vectors, "vector_store_metadata", None)
    vector_store_backend = None
    vector_store_uri = None
    vector_store_index_params = None
    vector_store_consistency = None
    if isinstance(vector_store_metadata, dict):
        vector_store_backend = vector_store_metadata.get("backend")
        vector_store_uri = vector_store_metadata.get("uri_redacted")
        vector_store_index_params = vector_store_metadata.get("index_params")
        vector_store_consistency = vector_store_metadata.get("consistency")
    embedding_metadata = dict(vector.metadata or ())
    plan = artifact.execution_plan
    determinism_hash = determinism_fingerprint(
        artifact.vector_fingerprint,
        artifact.index_config_fingerprint,
        plan.algorithm if plan else None,
    )

    return {
        "document": document,
        "chunk": chunk,
        "vector": vector,
        "artifact": artifact,
        "metric": artifact.metric,
        "score": result.score,
        "correlation_id": result.request_id,
        "execution_contract": artifact.execution_contract,
        "execution_contract_status": execution_contract_status,
        "replayable": artifact.replayable,
        "execution_id": artifact.execution_id,
        "nondeterministic_sources": nondeterministic_sources,
        "lossy_dimensions": lossy_dimensions,
        "embedding_source": vector.model,
        "embedding_determinism": embedding_metadata.get("embedding_determinism"),
        "embedding_seed": embedding_metadata.get("embedding_seed"),
        "embedding_model_version": embedding_metadata.get("embedding_model_version"),
        "embedding_provider": embedding_metadata.get("embedding_provider"),
        "embedding_provider_version": embedding_metadata.get(
            "embedding_provider_version"
        ),
        "embedding_device": embedding_metadata.get("embedding_device"),
        "embedding_dtype": embedding_metadata.get("embedding_dtype"),
        "embedding_normalization": embedding_metadata.get("embedding_normalization"),
        "vector_store_backend": vector_store_backend,
        "vector_store_uri_redacted": vector_store_uri,
        "vector_store_index_params": vector_store_index_params,
        "vector_store_consistency": vector_store_consistency,
        "determinism_fingerprint": determinism_hash,
    }
