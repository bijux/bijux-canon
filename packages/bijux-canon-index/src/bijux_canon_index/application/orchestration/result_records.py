# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Artifact metadata and run-record helpers for orchestration."""

from __future__ import annotations

from dataclasses import asdict, replace
from typing import Any

from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.types import ExecutionArtifact


def artifact_build_params(
    *, vector_store_enabled: bool, stores: Any
) -> tuple[tuple[str, str], ...]:
    if not vector_store_enabled:
        return ()
    metadata = getattr(stores.vectors, "vector_store_metadata", None)
    if not isinstance(metadata, dict):
        return ()
    params: list[tuple[str, str]] = []
    backend = metadata.get("backend")
    if backend:
        params.append(("vector_store.backend", str(backend)))
    uri = metadata.get("uri_redacted")
    if uri:
        params.append(("vector_store.uri_redacted", str(uri)))
    index_params = metadata.get("index_params")
    if index_params:
        params.append(("vector_store.index_params", str(index_params)))
    return tuple(params)


def metadata_tuple(
    meta: dict[str, str | None],
) -> tuple[tuple[str, str], ...] | None:
    items = tuple((key, value) for key, value in meta.items() if value is not None)
    return items or None


def build_run_metadata(
    req: Any,
    *,
    artifact: ExecutionArtifact,
    ann_index_info: dict[str, object] | None,
    vector_store_resolution: Any,
    vector_store_consistency: str | None,
    backend_name: str,
    backend_fingerprint: str,
    determinism_fingerprint: str,
    correlation_id: str,
) -> dict[str, object]:
    return {
        "execution_id": correlation_id,
        "artifact_id": artifact.artifact_id,
        "request": {
            "request_text": req.request_text,
            "vector_dim": len(req.vector or ()),
            "top_k": req.top_k,
            "execution_contract": req.execution_contract.value,
            "execution_intent": req.execution_intent.value,
            "execution_mode": req.execution_mode.value,
            "nd_witness_rate": req.nd_witness_rate,
            "nd_witness_sample_k": req.nd_witness_sample_k,
            "nd_witness_mode": req.nd_witness_mode,
            "nd_build_on_demand": req.nd_build_on_demand,
            "nd_candidate_k": req.nd_candidate_k,
            "nd_diversity_lambda": req.nd_diversity_lambda,
            "nd_outlier_threshold": req.nd_outlier_threshold,
            "nd_low_signal_margin": req.nd_low_signal_margin,
            "nd_adaptive_k": req.nd_adaptive_k,
            "nd_low_signal_refuse": req.nd_low_signal_refuse,
            "nd_two_stage": req.nd_two_stage,
            "nd_profile": req.nd_profile,
            "nd_target_recall": req.nd_target_recall,
            "nd_latency_budget_ms": req.nd_latency_budget_ms,
            "nd_m": req.nd_m,
            "nd_ef_construction": req.nd_ef_construction,
            "nd_ef_search": req.nd_ef_search,
            "nd_max_ef_search": req.nd_max_ef_search,
            "nd_space": req.nd_space,
        },
        "backend": backend_name,
        "vector_store": {
            "backend": vector_store_resolution.descriptor.name,
            "uri_redacted": vector_store_resolution.uri_redacted,
            "supports_exact": vector_store_resolution.descriptor.supports_exact,
            "supports_ann": vector_store_resolution.descriptor.supports_ann,
            "consistency": vector_store_consistency,
        },
        "ann_index": ann_index_info,
        "determinism_fingerprints": {
            "vectors": artifact.vector_fingerprint,
            "config": artifact.index_config_fingerprint,
            "backend": backend_fingerprint,
            "determinism": determinism_fingerprint,
        },
    }


def finalize_execution(
    *,
    tx_factory: Any,
    stores: Any,
    run_store: Any,
    artifact: ExecutionArtifact,
    execution_result: Any,
    results: Any,
    run_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    with tx_factory() as tx:
        tx = tx  # help type checkers keep the protocol visible
        stores.ledger.put_execution_result(tx, execution_result)
        updated_artifact = replace(
            artifact,
            execution_plan=execution_result.plan,
            execution_signature=execution_result.signature,
            execution_id=execution_result.execution_id,
        )
        stores.ledger.put_artifact(tx, updated_artifact)
        artifact = updated_artifact
    nd_trace = None
    if execution_result.nd_result is not None:
        trace = execution_result.nd_result.decision_trace
        if trace is not None:
            nd_trace = asdict(trace)
    run_store.finalize(
        run_id,
        {
            "execution_result": execution_result.to_primitive(),
            "results": [result.vector_id for result in results],
            "nd_decision_trace": nd_trace,
        },
    )
    return {
        "results": [result.vector_id for result in results],
        "correlation_id": correlation_id,
        "execution_contract": artifact.execution_contract.value,
        "execution_contract_status": (
            "stable"
            if artifact.execution_contract is ExecutionContract.DETERMINISTIC
            else "experimental"
        ),
        "replayable": artifact.replayable,
        "execution_id": execution_result.execution_id,
    }


__all__ = [
    "artifact_build_params",
    "build_run_metadata",
    "finalize_execution",
    "metadata_tuple",
]
