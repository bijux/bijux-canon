# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Execution payloads helpers for the CLI interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.errors import ValidationError
from bijux_canon_index.core.runtime.vector_execution import RandomnessProfile
from bijux_canon_index.core.types import ExecutionBudget
from bijux_canon_index.interfaces.cli.configuration import (
    parse_contract,
    parse_intent,
    parse_mode,
)
from bijux_canon_index.interfaces.schemas.requests import (
    ExecutionBudgetPayload,
    ExecutionRequestPayload,
    RandomnessProfilePayload,
)


def build_execute_payload(
    *,
    request_text: str | None,
    vector: str | None,
    top_k: int,
    artifact_id: str,
    execution_contract: str,
    execution_intent: str,
    execution_mode: str,
    randomness_seed: int | None,
    randomness_sources: str | None,
    randomness_bounded: bool,
    randomness_non_replayable: bool,
    max_latency_ms: int | None,
    max_memory_mb: int | None,
    max_error: float | None,
    vector_store: str | None,
    vector_store_uri: str | None,
    nd_profile: str | None,
    nd_target_recall: float | None,
    nd_latency_budget_ms: int | None,
    nd_witness_rate: float | None,
    nd_witness_sample_k: int | None,
    nd_witness_mode: str | None,
    nd_build_on_demand: bool,
    nd_candidate_k: int | None,
    nd_diversity_lambda: float | None,
    nd_normalize_vectors: bool,
    nd_normalize_query: bool,
    nd_outlier_threshold: float | None,
    nd_low_signal_margin: float | None,
    nd_adaptive_k: bool,
    nd_low_signal_refuse: bool,
    nd_replay_strict: bool,
    nd_warmup_queries: Path | None,
    nd_incremental_index: bool | None,
    nd_max_candidates: int | None,
    nd_max_index_memory_mb: int | None,
    nd_two_stage: bool,
    nd_m: int | None,
    nd_ef_construction: int | None,
    nd_ef_search: int | None,
    nd_max_ef_search: int | None,
    nd_space: str | None,
    correlation_id: str,
) -> tuple[ExecutionRequestPayload, ExecutionContract]:
    """Build execute payload."""
    vector_parsed = json.loads(vector) if vector else None
    contract = parse_contract(execution_contract)
    sources = parse_randomness_sources(randomness_sources)
    payload = ExecutionRequestPayload(
        request_text=request_text,
        vector=tuple(vector_parsed) if vector_parsed else None,
        top_k=top_k,
        artifact_id=artifact_id,
        execution_contract=contract,
        execution_intent=parse_intent(execution_intent),
        execution_mode=parse_mode(execution_mode),
        randomness_profile=RandomnessProfilePayload.model_validate(
            {
                "seed": randomness_seed,
                "sources": sources,
                "bounded": randomness_bounded,
                "non_replayable": randomness_non_replayable,
            }
        )
        if contract is ExecutionContract.NON_DETERMINISTIC
        else None,
        execution_budget=ExecutionBudgetPayload(
            max_latency_ms=max_latency_ms,
            max_memory_mb=max_memory_mb,
            max_error=max_error,
        ),
        nd_profile=nd_profile,
        nd_target_recall=nd_target_recall,
        nd_latency_budget_ms=nd_latency_budget_ms,
        nd_witness_rate=nd_witness_rate,
        nd_witness_sample_k=nd_witness_sample_k,
        nd_witness_mode=nd_witness_mode,
        nd_build_on_demand=nd_build_on_demand,
        nd_candidate_k=nd_candidate_k,
        nd_diversity_lambda=nd_diversity_lambda,
        nd_normalize_vectors=nd_normalize_vectors,
        nd_normalize_query=nd_normalize_query,
        nd_outlier_threshold=nd_outlier_threshold,
        nd_low_signal_margin=nd_low_signal_margin,
        nd_adaptive_k=nd_adaptive_k,
        nd_low_signal_refuse=nd_low_signal_refuse,
        nd_replay_strict=nd_replay_strict,
        nd_warmup_queries=str(nd_warmup_queries) if nd_warmup_queries else None,
        nd_incremental_index=nd_incremental_index,
        nd_max_candidates=nd_max_candidates,
        nd_max_index_memory_mb=nd_max_index_memory_mb,
        nd_two_stage=nd_two_stage,
        nd_m=nd_m,
        nd_ef_construction=nd_ef_construction,
        nd_ef_search=nd_ef_search,
        nd_max_ef_search=nd_max_ef_search,
        nd_space=nd_space,
        correlation_id=correlation_id,
        vector_store=vector_store,
        vector_store_uri=vector_store_uri,
    )
    return payload, contract


def build_replay_runtime(
    *,
    randomness_seed: int | None,
    randomness_sources: str | None,
    randomness_bounded: bool,
    randomness_non_replayable: bool,
    max_latency_ms: int | None,
    max_memory_mb: int | None,
    max_error: float | None,
) -> tuple[RandomnessProfile, ExecutionBudget]:
    """Build replay runtime."""
    sources = parse_randomness_sources(randomness_sources)
    return (
        RandomnessProfile(
            seed=randomness_seed,
            sources=tuple(sources or ()),
            bounded=randomness_bounded,
            non_replayable=randomness_non_replayable,
        ),
        ExecutionBudget(
            max_latency_ms=max_latency_ms,
            max_memory_mb=max_memory_mb,
            max_error=max_error,
        ),
    )


def build_artifact_compare_payload(
    *,
    vector: str,
    top_k: int,
    execution_intent: str,
    execution_contract: str,
    vector_store: str | None,
    vector_store_uri: str | None,
) -> ExecutionRequestPayload:
    """Build artifact compare payload."""
    return ExecutionRequestPayload(
        request_text=None,
        vector=tuple(json.loads(vector)),
        top_k=top_k,
        execution_contract=parse_contract(execution_contract),
        execution_intent=parse_intent(execution_intent),
        vector_store=vector_store,
        vector_store_uri=vector_store_uri,
    )


def build_run_or_bundle_comparison(
    *,
    run_a: str | None,
    run_b: str | None,
    bundle_a: Path | None,
    bundle_b: Path | None,
    load_run: callable,
    load_bundle: callable,
) -> dict[str, object] | None:
    """Build run or bundle comparison."""
    if not (run_a or run_b or bundle_a or bundle_b):
        return None
    if not (run_a and run_b) and not (bundle_a and bundle_b):
        raise ValidationError(
            message="compare requires both --run-a/--run-b or both --bundle-a/--bundle-b"
        )
    if run_a and run_b:
        rec_a = load_run(run_a)
        rec_b = load_run(run_b)
        results_a = extract_results(rec_a.result if rec_a.result else {})
        results_b = extract_results(rec_b.result if rec_b.result else {})
        meta_a = ensure_metadata(rec_a.metadata)
        meta_b = ensure_metadata(rec_b.metadata)
    else:
        if bundle_a is None or bundle_b is None:
            raise ValidationError(
                message="compare requires both --run-a/--run-b or both --bundle-a/--bundle-b"
            )
        bundle_a_data = load_bundle(bundle_a)
        bundle_b_data = load_bundle(bundle_b)
        results_a = extract_results(bundle_a_data.get("result", {}))
        results_b = extract_results(bundle_b_data.get("result", {}))
        meta_a = ensure_metadata(bundle_a_data.get("metadata", {}))
        meta_b = ensure_metadata(bundle_b_data.get("metadata", {}))
    set_a = set(results_a)
    set_b = set(results_b)
    overlap = set_a & set_b
    union = set_a | set_b
    return {
        "execution_a": meta_a.get("execution_id"),
        "execution_b": meta_b.get("execution_id"),
        "overlap_ratio": len(overlap) / len(union) if union else 1.0,
        "recall_delta": (len(overlap) / len(set_a) if set_a else 1.0)
        - (len(overlap) / len(set_b) if set_b else 1.0),
        "execution_contract_diff": {
            "a": nested_metadata(meta_a, "request", "execution_contract"),
            "b": nested_metadata(meta_b, "request", "execution_contract"),
        },
        "backend_diff": {
            "a": meta_a.get("backend"),
            "b": meta_b.get("backend"),
        },
        "vector_store_diff": {
            "a": meta_a.get("vector_store", {}),
            "b": meta_b.get("vector_store", {}),
        },
    }


def parse_randomness_sources(raw: str | None) -> list[str] | None:
    """Parse randomness sources."""
    if not raw:
        return None
    return [segment.strip() for segment in raw.split(",")]


def extract_results(result_payload: object) -> list[str]:
    """Extract results."""
    if not isinstance(result_payload, dict):
        return []
    results = result_payload.get("results", [])
    if not isinstance(results, list):
        return []
    return [item for item in results if isinstance(item, str)]


def ensure_metadata(metadata: object) -> dict[str, Any]:
    """Ensure metadata."""
    if isinstance(metadata, dict):
        return dict(metadata)
    return {}


def nested_metadata(metadata: dict[str, Any], *path: str) -> object:
    """Handle nested metadata."""
    current: object = metadata
    for part in path:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


__all__ = [
    "build_artifact_compare_payload",
    "build_execute_payload",
    "build_replay_runtime",
    "build_run_or_bundle_comparison",
]
