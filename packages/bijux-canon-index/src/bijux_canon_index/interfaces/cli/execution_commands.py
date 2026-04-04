# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Primary execution-oriented CLI commands."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import typer

from bijux_canon_index.application.engine import VectorExecutionEngine
from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.errors import BijuxError, ValidationError
from bijux_canon_index.infra.adapters.vectorstore_registry import VECTOR_STORES
from bijux_canon_index.infra.embeddings.registry import EMBEDDING_PROVIDERS
from bijux_canon_index.infra.run_store import RunStore
from bijux_canon_index.interfaces.cli.ingest_commands import ingest, materialize
from bijux_canon_index.interfaces.cli.workspace_commands import (
    audit,
    capabilities,
    init,
    list_artifacts,
    list_runs,
)
from bijux_canon_index.interfaces.cli.configuration import (
    build_config as _build_config,
)
from bijux_canon_index.interfaces.cli.configuration import (
    load_config as _load_config,
)
from bijux_canon_index.interfaces.cli.configuration import (
    parse_contract as _parse_contract,
)
from bijux_canon_index.interfaces.cli.execution_payloads import (
    build_artifact_compare_payload,
    build_execute_payload,
    build_replay_runtime,
    build_run_or_bundle_comparison,
)
from bijux_canon_index.interfaces.cli.options import ND_WARMUP_OPTION
from bijux_canon_index.interfaces.cli.rendering import (
    config_to_dict as _config_to_dict,
)
from bijux_canon_index.interfaces.cli.rendering import (
    emit as _emit,
)
from bijux_canon_index.interfaces.cli.rendering import (
    load_bundle as _load_bundle,
)
from bijux_canon_index.interfaces.cli.rendering import (
    resolve_correlation_id as _resolve_correlation_id,
)
from bijux_canon_index.interfaces.errors import (
    is_refusal,
    refusal_payload,
    to_cli_exit,
)
from bijux_canon_index.interfaces.errors.reporting import record_failure
from bijux_canon_index.interfaces.schemas.requests import ExplainRequest


def register_execution_commands(app: typer.Typer) -> None:
    app.command()(list_artifacts)
    app.command()(list_runs)
    app.command()(init)
    app.command()(capabilities)
    app.command()(audit)
    app.command()(ingest)
    app.command()(validate)
    app.command()(doctor)
    app.command()(materialize)
    app.command()(execute)
    app.command()(explain)
    app.command()(replay)
    app.command()(compare)


def validate(
    ctx: typer.Context,
    doc: list[str] = typer.Option(None, "--doc"),  # noqa: B008
    vector: list[str] = typer.Option(None, "--vector"),  # noqa: B008
    execution_contract: str | None = typer.Option(None, "--execution-contract"),
    vector_store: str | None = typer.Option(None, "--vector-store"),
    vector_store_uri: str | None = typer.Option(None, "--vector-store-uri"),
) -> None:
    try:
        docs = doc or []
        vectors = [json.loads(v) for v in (vector or [])]
        if docs and vectors and len(docs) != len(vectors):
            raise ValidationError(message="doc/vector alignment mismatch")
        if vectors:
            dims = {len(v) for v in vectors}
            if len(dims) != 1:
                raise ValidationError(message="vectors have inconsistent dimensions")
        base_config = _load_config(ctx.obj.config_path) if ctx.obj else None
        config = _build_config(
            vector_store=vector_store,
            vector_store_uri=vector_store_uri,
            base_config=base_config,
        )
        if config.vector_store:
            VECTOR_STORES.resolve(
                config.vector_store.backend or "memory",
                uri=config.vector_store.uri,
                options=config.vector_store.options,
            )
        if execution_contract:
            contract = _parse_contract(execution_contract)
            if config.vector_store:
                desc = VECTOR_STORES.resolve(
                    config.vector_store.backend or "memory",
                    uri=config.vector_store.uri,
                    options=config.vector_store.options,
                ).descriptor
                if (
                    contract is ExecutionContract.DETERMINISTIC
                    and not desc.deterministic_exact
                ):
                    raise ValidationError(
                        message="deterministic contract requires deterministic vector store"
                    )
                if (
                    contract is ExecutionContract.NON_DETERMINISTIC
                    and not desc.supports_ann
                ):
                    raise ValidationError(
                        message="non_deterministic contract requires ANN-capable vector store"
                    )
        _emit(ctx, {"status": "valid"})
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


def doctor(
    ctx: typer.Context,
    vector_store: str | None = typer.Option(None, "--vector-store"),
    vector_store_uri: str | None = typer.Option(None, "--vector-store-uri"),
) -> None:
    try:
        extras = {}
        for module in ("faiss", "qdrant_client", "sentence_transformers"):
            try:
                __import__(module)
                extras[module] = True
            except Exception:
                extras[module] = False
        base_config = _load_config(ctx.obj.config_path) if ctx.obj else None
        config = _build_config(
            vector_store=vector_store,
            vector_store_uri=vector_store_uri,
            base_config=base_config,
        )
        backend_status = {"configured": False}
        if config.vector_store:
            backend_status["configured"] = True
            resolution = VECTOR_STORES.resolve(
                config.vector_store.backend or "memory",
                uri=config.vector_store.uri,
                options=config.vector_store.options,
            )
            backend_status.update(
                {
                    "backend": resolution.descriptor.name,
                    "available": resolution.descriptor.available,
                    "uri_redacted": resolution.uri_redacted,
                }
            )
            adapter = resolution.adapter
            if hasattr(adapter, "status"):
                backend_status["status"] = adapter.status()
        run_dir = RunStore()._base
        workspace = Path.cwd()
        permissions = {
            "workspace_writable": os.access(workspace, os.W_OK),
            "run_dir_writable": os.access(run_dir, os.W_OK)
            if run_dir.exists()
            else True,
        }
        report = {
            "extras": extras,
            "backend": backend_status,
            "embeddings": {"providers": EMBEDDING_PROVIDERS.providers()},
            "permissions": permissions,
        }
        _emit(ctx, report)
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)




def execute(
    ctx: typer.Context,
    request_text: str | None = None,
    vector: str | None = None,
    top_k: int = 5,
    artifact_id: str = typer.Option(
        "art-1", "--artifact-id", help="Target execution artifact id"
    ),
    execution_contract: str = typer.Option(
        ...,
        "--execution-contract",
        help="Execution contract (deterministic preferred; non_deterministic is approximate)",
    ),
    execution_intent: str = typer.Option(
        ...,
        "--execution-intent",
        help="Execution intent (explains why determinism or loss is acceptable)",
    ),
    execution_mode: str = typer.Option(
        "strict",
        "--execution-mode",
        help="Execution mode: strict|bounded|exploratory",
    ),
    randomness_seed: int | None = typer.Option(None, "--randomness-seed"),
    randomness_sources: str | None = typer.Option(
        None,
        "--randomness-sources",
        help="Comma-separated randomness sources (required for non_deterministic)",
    ),
    randomness_bounded: bool = typer.Option(
        False, "--randomness-bounded", help="Whether randomness is bounded"
    ),
    randomness_non_replayable: bool = typer.Option(
        False,
        "--randomness-non-replayable",
        help="Declare ND run as non-replayable without a seed",
    ),
    max_latency_ms: int | None = typer.Option(None, "--max-latency-ms"),
    max_memory_mb: int | None = typer.Option(None, "--max-memory-mb"),
    max_error: float | None = typer.Option(None, "--max-error"),
    vector_store: str | None = typer.Option(None, "--vector-store"),
    vector_store_uri: str | None = typer.Option(None, "--vector-store-uri"),
    nd_profile: str | None = typer.Option(
        None, "--nd-profile", help="ND search profile: fast|balanced|accurate"
    ),
    nd_target_recall: float | None = typer.Option(
        None, "--nd-target-recall", help="ND target recall (0-1]"
    ),
    nd_latency_budget_ms: int | None = typer.Option(
        None, "--nd-latency-budget-ms", help="ND latency budget in ms"
    ),
    nd_witness_rate: float | None = typer.Option(
        None, "--nd-witness-rate", help="Fraction of ND runs to witness (0-1]"
    ),
    nd_witness_sample_k: int | None = typer.Option(
        None, "--nd-witness-sample-k", help="Exact witness top-k sample size"
    ),
    nd_witness_mode: str | None = typer.Option(
        None, "--nd-witness-mode", help="Witness mode: off|sample|full"
    ),
    nd_build_on_demand: bool = typer.Option(
        False, "--nd-build-on-demand", help="Build ANN index on demand"
    ),
    nd_candidate_k: int | None = typer.Option(
        None, "--nd-candidate-k", help="ANN candidate pool size for reranking"
    ),
    nd_diversity_lambda: float | None = typer.Option(
        None, "--nd-diversity-lambda", help="MMR diversity lambda (0-1)"
    ),
    nd_normalize_vectors: bool = typer.Option(
        False, "--nd-normalize-vectors", help="Normalize candidate vectors"
    ),
    nd_normalize_query: bool = typer.Option(
        False, "--nd-normalize-query", help="Normalize query vector"
    ),
    nd_outlier_threshold: float | None = typer.Option(
        None, "--nd-outlier-threshold", help="Low-signal similarity threshold"
    ),
    nd_low_signal_margin: float | None = typer.Option(
        None, "--nd-low-signal-margin", help="Low-signal distance margin threshold"
    ),
    nd_adaptive_k: bool = typer.Option(
        False, "--nd-adaptive-k", help="Allow adaptive k below requested top_k"
    ),
    nd_low_signal_refuse: bool = typer.Option(
        False, "--nd-low-signal-refuse", help="Refuse ND when signal is too low"
    ),
    nd_replay_strict: bool = typer.Option(
        False, "--nd-replay-strict", help="Refuse replay if index/params differ"
    ),
    nd_warmup_queries: Path | None = ND_WARMUP_OPTION,
    nd_incremental_index: bool | None = typer.Option(
        None,
        "--nd-incremental-index/--nd-no-incremental-index",
        help="Allow incremental index updates",
    ),
    nd_max_candidates: int | None = typer.Option(
        None, "--nd-max-candidates", help="Hard cap for ANN candidates"
    ),
    nd_max_index_memory_mb: int | None = typer.Option(
        None,
        "--nd-max-index-memory-mb",
        help="Hard cap for ANN index memory (MB)",
    ),
    nd_two_stage: bool = typer.Option(
        True,
        "--nd-two-stage/--no-nd-two-stage",
        help="Enable ANN candidate rerank with exact scoring",
    ),
    nd_m: int | None = typer.Option(None, "--nd-m", help="HNSW M parameter"),
    nd_ef_construction: int | None = typer.Option(
        None, "--nd-ef-construction", help="HNSW ef_construction parameter"
    ),
    nd_ef_search: int | None = typer.Option(
        None, "--nd-ef-search", help="HNSW ef_search parameter"
    ),
    nd_max_ef_search: int | None = typer.Option(
        None, "--nd-max-ef-search", help="Max HNSW ef_search (hard cap)"
    ),
    nd_space: str | None = typer.Option(
        None, "--nd-space", help="HNSW space override: l2|cosine|ip"
    ),
    compare_to: str | None = typer.Option(
        None, "--compare-to", help="Compare ND run to exact (exact)"
    ),
    compare_artifact_id: str | None = typer.Option(
        None, "--compare-artifact-id", help="Deterministic artifact id for compare"
    ),
    correlation_id: str | None = typer.Option(None, "--correlation-id"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    explain: bool = typer.Option(False, "--explain"),
) -> None:
    try:
        resolved_correlation_id = _resolve_correlation_id(correlation_id)
        req, contract = build_execute_payload(
            request_text=request_text,
            vector=vector,
            top_k=top_k,
            artifact_id=artifact_id,
            execution_contract=execution_contract,
            execution_intent=execution_intent,
            execution_mode=execution_mode,
            randomness_seed=randomness_seed,
            randomness_sources=randomness_sources,
            randomness_bounded=randomness_bounded,
            randomness_non_replayable=randomness_non_replayable,
            max_latency_ms=max_latency_ms,
            max_memory_mb=max_memory_mb,
            max_error=max_error,
            vector_store=vector_store,
            vector_store_uri=vector_store_uri,
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
            nd_warmup_queries=nd_warmup_queries,
            nd_incremental_index=nd_incremental_index,
            nd_max_candidates=nd_max_candidates,
            nd_max_index_memory_mb=nd_max_index_memory_mb,
            nd_two_stage=nd_two_stage,
            nd_m=nd_m,
            nd_ef_construction=nd_ef_construction,
            nd_ef_search=nd_ef_search,
            nd_max_ef_search=nd_max_ef_search,
            nd_space=nd_space,
            correlation_id=resolved_correlation_id,
        )
        base_config = _load_config(ctx.obj.config_path) if ctx.obj else None
        config = _build_config(
            vector_store=vector_store,
            vector_store_uri=vector_store_uri,
            base_config=base_config,
        )
        if dry_run:
            vs_descriptor = None
            if config.vector_store:
                store_name = config.vector_store.backend
                vs_descriptor = next(
                    (d for d in VECTOR_STORES.descriptors() if d.name == store_name),
                    None,
                )
            output = {
                "resolved_config": _config_to_dict(config),
                "determinism": contract.value,
                "vector_store": vs_descriptor.name if vs_descriptor else None,
                "provenance_fields": [
                    "execution_id",
                    "result_id",
                    "vector_store_backend",
                    "vector_store_uri_redacted",
                    "vector_store_index_params",
                ],
            }
            _emit(ctx, output)
            return
        if compare_to is not None and compare_to != "exact":
            raise ValidationError(message="compare-to supports only 'exact'")
        if compare_to == "exact" and not compare_artifact_id:
            raise ValidationError(
                message="compare-to exact requires --compare-artifact-id"
            )
        engine = VectorExecutionEngine(config=config)
        result = engine.execute(req)
        if compare_to == "exact":
            comparison = engine.compare(
                req,
                artifact_a_id=artifact_id,
                artifact_b_id=compare_artifact_id,
            )
            _emit(ctx, {"execution": result, "compare": comparison})
            return
        if explain:
            results = result.get("results", [])
            if not results:
                raise ValidationError(message="No results available to explain")
            explain_result = engine.explain(ExplainRequest(result_id=results[0]))
            _emit(ctx, {"result": result, "explain": explain_result})
            return
        _emit(ctx, result)
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


def explain(
    ctx: typer.Context, result_id: str = typer.Option(..., "--result-id")
) -> None:
    try:
        req = ExplainRequest(result_id=result_id)
        engine = VectorExecutionEngine()
        result = engine.explain(req)
        _emit(ctx, result)
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


def replay(
    ctx: typer.Context,
    request_text: str = typer.Option(..., "--request-text"),
    randomness_seed: int | None = typer.Option(None, "--randomness-seed"),
    randomness_sources: str | None = typer.Option(
        None,
        "--randomness-sources",
        help="Comma-separated randomness sources (required for non_deterministic)",
    ),
    randomness_bounded: bool = typer.Option(
        False, "--randomness-bounded", help="Whether randomness is bounded"
    ),
    randomness_non_replayable: bool = typer.Option(
        False,
        "--randomness-non-replayable",
        help="Declare ND run as non-replayable without a seed",
    ),
    max_latency_ms: int | None = typer.Option(None, "--max-latency-ms"),
    max_memory_mb: int | None = typer.Option(None, "--max-memory-mb"),
    max_error: float | None = typer.Option(None, "--max-error"),
) -> None:
    try:
        engine = VectorExecutionEngine()
        randomness_profile, execution_budget = build_replay_runtime(
            randomness_seed=randomness_seed,
            randomness_sources=randomness_sources,
            randomness_bounded=randomness_bounded,
            randomness_non_replayable=randomness_non_replayable,
            max_latency_ms=max_latency_ms,
            max_memory_mb=max_memory_mb,
            max_error=max_error,
        )
        result = engine.replay(
            request_text,
            randomness_profile=randomness_profile,
            execution_budget=execution_budget,
        )
        _emit(ctx, result)
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


def compare(
    ctx: typer.Context,
    vector: str | None = typer.Option(None, "--vector"),
    top_k: int = 5,
    execution_intent: str = typer.Option(
        ...,
        "--execution-intent",
        help="Execution intent for the comparison request",
    ),
    execution_contract: str = typer.Option(
        "deterministic",
        "--execution-contract",
        help="Contract placeholder for payload validation; artifacts govern actual contract",
    ),
    artifact_a: str = typer.Option("art-1", "--artifact-a"),
    artifact_b: str = typer.Option("art-1", "--artifact-b"),
    vector_store: str | None = typer.Option(None, "--vector-store"),
    vector_store_uri: str | None = typer.Option(None, "--vector-store-uri"),
    run_a: str | None = typer.Option(None, "--run-a"),
    run_b: str | None = typer.Option(None, "--run-b"),
    bundle_a: Path | None = typer.Option(None, "--bundle-a"),  # noqa: B008
    bundle_b: Path | None = typer.Option(None, "--bundle-b"),  # noqa: B008
) -> None:
    try:
        comparison = build_run_or_bundle_comparison(
            run_a=run_a,
            run_b=run_b,
            bundle_a=bundle_a,
            bundle_b=bundle_b,
            load_run=RunStore().load,
            load_bundle=_load_bundle,
        )
        if comparison is not None:
            _emit(ctx, comparison)
            return
        if vector is None:
            raise ValidationError(message="--vector required for artifact comparison")
        payload = build_artifact_compare_payload(
            vector=vector,
            top_k=top_k,
            execution_intent=execution_intent,
            execution_contract=execution_contract,
            vector_store=vector_store,
            vector_store_uri=vector_store_uri,
        )
        base_config = _load_config(ctx.obj.config_path) if ctx.obj else None
        engine = VectorExecutionEngine(
            config=_build_config(
                vector_store=vector_store,
                vector_store_uri=vector_store_uri,
                base_config=base_config,
            )
        )
        result = engine.compare(
            payload, artifact_a_id=artifact_a, artifact_b_id=artifact_b
        )
        _emit(ctx, result)
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


__all__ = ["register_execution_commands"]
