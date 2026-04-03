# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
import os
from pathlib import Path
from statistics import mean
import sys
import time
from typing import no_type_check
import uuid
import zipfile

import typer

from bijux_vex.bench.dataset import (
    DEFAULT_DIMENSION,
    DEFAULT_QUERY_COUNT,
    DEFAULT_SEED,
    dataset_folder,
    generate_dataset,
    load_dataset,
    save_dataset,
)
from bijux_vex.bench.runner import format_table, run_benchmark
from bijux_vex.boundaries.exception_bridge import (
    is_refusal,
    record_failure,
    refusal_payload,
    to_cli_exit,
)
from bijux_vex.boundaries.pydantic_edges.models import (
    ExecutionArtifactRequest,
    ExecutionBudgetPayload,
    ExecutionRequestPayload,
    ExplainRequest,
    IngestRequest,
    RandomnessProfilePayload,
)
from bijux_vex.core.config import (
    EmbeddingCacheConfig,
    EmbeddingConfig,
    ExecutionConfig,
    ResourceLimits,
    VectorStoreConfig,
)
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import BijuxError, ValidationError
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.identity.ids import fingerprint
from bijux_vex.core.runtime.vector_execution import RandomnessProfile
from bijux_vex.core.types import ExecutionBudget, ExecutionRequest, NDSettings, Result
from bijux_vex.domain.execution_requests import scoring
from bijux_vex.domain.execution_requests.compare import _rank_instability
from bijux_vex.infra.adapters.vectorstore_registry import VECTOR_STORES
from bijux_vex.infra.embeddings.registry import EMBEDDING_PROVIDERS
from bijux_vex.infra.logging import enable_trace, trace_events
from bijux_vex.infra.metrics import METRICS
from bijux_vex.infra.run_store import RunStore
from bijux_vex.services.execution_engine import VectorExecutionEngine

app = typer.Typer(add_completion=False)
vdb_app = typer.Typer(add_completion=False, help="Vector DB utilities")
app.add_typer(vdb_app, name="vdb")
nd_app = typer.Typer(add_completion=False, help="ND utilities")
app.add_typer(nd_app, name="nd")
config_app = typer.Typer(add_completion=False, help="Configuration utilities")
app.add_typer(config_app, name="config")
artifact_app = typer.Typer(add_completion=False, help="Artifact bundle utilities")
app.add_typer(artifact_app, name="artifact")

ND_WARMUP_OPTION = typer.Option(
    None, "--nd-warmup-queries", help="Path to JSON warmup query vectors"
)
ND_TUNE_CACHE_OPTION = typer.Option(
    None, "--cache", help="Optional path to cache tuning results"
)
ND_TUNE_DATASET_DIR_OPTION = typer.Option(
    None, "--dataset-dir", help="Path to dataset directory for tuning"
)


@dataclass(frozen=True)
class OutputOptions:
    fmt: str | None = None
    output: Path | None = None
    config_path: Path | None = None
    trace: bool = False
    quiet: bool = False
    no_color: bool = False


@app.callback()
@no_type_check
def _main_callback(
    ctx: typer.Context,
    fmt: str | None = typer.Option(
        None, "--format", help="Output format: json|table (default: json)"
    ),
    output: Path | None = typer.Option(  # noqa: B008
        None, "--output", help="Write output to a file"
    ),
    config: Path | None = typer.Option(  # noqa: B008
        None, "--config", help="Load configuration from a TOML/YAML file"
    ),
    trace: bool = typer.Option(False, "--trace", help="Emit trace metadata"),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress non-error output"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output"),
) -> None:
    if trace:
        enable_trace()
    if no_color:
        os.environ["RICH_NO_COLOR"] = "1"
        os.environ["TYPER_COLOR"] = "0"
    ctx.obj = OutputOptions(
        fmt=fmt,
        output=output,
        config_path=config,
        trace=trace,
        quiet=quiet,
        no_color=no_color,
    )


def _render_table(data: object) -> str:
    if isinstance(data, dict):
        lines = ["key | value", "---- | -----"]
        for key, value in data.items():
            lines.append(f"{key} | {value}")
        return "\n".join(lines)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        keys = list(data[0].keys())
        header = " | ".join(keys)
        divider = " | ".join(["---"] * len(keys))
        lines = [header, divider]
        lines.extend(" | ".join(str(row.get(k, "")) for k in keys) for row in data)
        return "\n".join(lines)
    return str(data)


def _resolve_correlation_id(raw: str | None) -> str:
    return raw or f"req-{uuid.uuid4().hex}"


def _emit(
    ctx: typer.Context | None,
    data: object,
    *,
    table: str | None = None,
) -> None:
    options: OutputOptions | None = getattr(ctx, "obj", None) if ctx else None
    fmt = options.fmt if options else None
    output = options.output if options else None
    quiet = options.quiet if options else False
    trace = options.trace if options else False
    payload: object = data
    if trace:
        payload = {"data": data, "trace": trace_events()}
    if fmt == "table":
        payload = table or _render_table(data)
        if not quiet:
            typer.echo(payload)
            if output:
                output.write_text(payload, encoding="utf-8")
        return
    if fmt is None and table is not None and not quiet:
        typer.echo(table)
    serialized = json.dumps(payload, default=str)
    if not quiet:
        typer.echo(serialized)
    if output:
        output.write_text(serialized, encoding="utf-8")


def _config_to_dict(config: ExecutionConfig | None) -> dict[str, object]:
    if config is None:
        return {}
    return asdict(config)


def _redact_config(config: ExecutionConfig | None) -> dict[str, object]:
    payload = _config_to_dict(config)
    vs = payload.get("vector_store")
    if isinstance(vs, dict) and vs.get("uri"):
        resolved = VECTOR_STORES.resolve(
            vs.get("backend") or "memory", uri=str(vs.get("uri"))
        )
        vs["uri"] = resolved.uri_redacted
    return payload


def _load_bundle(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path, "r") as zf:
        metadata = json.loads(zf.read("metadata.json").decode("utf-8"))
        result = json.loads(zf.read("result.json").decode("utf-8"))
        return {"metadata": metadata, "result": result}


def _parse_contract(raw: str) -> ExecutionContract:
    try:
        return ExecutionContract(raw)
    except Exception:
        typer.echo("execution-contract must be one of deterministic|non_deterministic")
        sys.exit(1)


def _parse_mode(raw: str) -> ExecutionMode:
    try:
        return ExecutionMode(raw)
    except Exception:
        typer.echo("execution-mode must be one of strict|bounded|exploratory")
        sys.exit(1)


ALLOWED_INTENTS = {intent.value for intent in ExecutionIntent}


def _parse_intent(raw: str) -> ExecutionIntent:
    if raw not in ALLOWED_INTENTS:
        allowed = "|".join(sorted(ALLOWED_INTENTS))
        typer.echo(f"execution-intent must be one of {allowed}")
        sys.exit(1)
    return ExecutionIntent(raw)


def _load_config(config_path: Path | None) -> ExecutionConfig | None:
    if not config_path:
        return None
    suffix = config_path.suffix.lower()
    if suffix in {".toml", ".tml"}:
        import tomllib

        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except Exception as exc:  # pragma: no cover
            raise ValueError(
                "YAML config requires PyYAML. Install with extras or use TOML."
            ) from exc
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    else:
        raise ValueError("config file must be .toml or .yaml/.yml")
    vector_store_cfg = payload.get("vector_store") or {}
    embed_cfg = payload.get("embeddings") or {}
    limits_cfg = payload.get("resource_limits") or {}
    cache_cfg = embed_cfg.get("cache") or {}
    vs_config = None
    if vector_store_cfg.get("backend"):
        vs_config = VectorStoreConfig(
            backend=vector_store_cfg.get("backend"),
            uri=vector_store_cfg.get("uri"),
        )
    embed_config = None
    if embed_cfg.get("provider") or embed_cfg.get("model") or cache_cfg.get("uri"):
        embed_config = EmbeddingConfig(
            provider=embed_cfg.get("provider"),
            model=embed_cfg.get("model"),
            cache=(
                EmbeddingCacheConfig(
                    backend=cache_cfg.get("backend"),
                    uri=cache_cfg.get("uri"),
                )
                if cache_cfg
                else None
            ),
        )
    limits = None
    if limits_cfg:
        limits = ResourceLimits(
            max_vectors_per_ingest=limits_cfg.get("max_vectors_per_ingest"),
            max_k=limits_cfg.get("max_k"),
            max_query_size=limits_cfg.get("max_query_size"),
            max_execution_time_ms=limits_cfg.get("max_execution_time_ms"),
        )
    return ExecutionConfig(
        vector_store=vs_config, embeddings=embed_config, resource_limits=limits
    )


def _build_config(
    *,
    vector_store: str | None = None,
    vector_store_uri: str | None = None,
    embed_provider: str | None = None,
    embed_model: str | None = None,
    cache_embeddings: str | None = None,
    base_config: ExecutionConfig | None = None,
) -> ExecutionConfig:
    vs_config = base_config.vector_store if base_config else None
    if vector_store:
        vs_config = VectorStoreConfig(backend=vector_store, uri=vector_store_uri)
    embed_config = base_config.embeddings if base_config else None
    if embed_model or embed_provider or cache_embeddings:
        cache_cfg = (
            EmbeddingCacheConfig(backend=None, uri=cache_embeddings)
            if cache_embeddings
            else None
        )
        embed_config = EmbeddingConfig(
            provider=embed_provider,
            model=embed_model,
            cache=cache_cfg,
        )
    limits = base_config.resource_limits if base_config else None
    return ExecutionConfig(
        vector_store=vs_config, embeddings=embed_config, resource_limits=limits
    )


@app.command()
@no_type_check
def list_artifacts(
    ctx: typer.Context,
    limit: int | None = typer.Option(None, "--limit"),
    offset: int = typer.Option(0, "--offset"),
) -> None:
    _emit(ctx, VectorExecutionEngine().list_artifacts(limit=limit, offset=offset))


@app.command()
@no_type_check
def list_runs(
    ctx: typer.Context,
    limit: int | None = typer.Option(None, "--limit"),
    offset: int = typer.Option(0, "--offset"),
) -> None:
    runs = RunStore().list_runs(limit=limit, offset=offset)
    _emit(ctx, {"runs": runs})


@app.command()
@no_type_check
def init(
    ctx: typer.Context,
    config_path: Path = typer.Option(  # noqa: B008
        Path("bijux_vex.toml"), "--config-path"
    ),
    force: bool = typer.Option(False, "--force"),
) -> None:
    config_template = """[vector_store]
backend = "memory"
# uri = "index.faiss"

[embeddings]
provider = "sentence_transformers"
model = "all-MiniLM-L6-v2"

[resource_limits]
# max_vectors_per_ingest = 10000
# max_k = 50
# max_query_size = 10000
# max_execution_time_ms = 2000
"""
    if config_path.exists() and not force:
        typer.echo("Config already exists. Use --force to overwrite.")
        sys.exit(1)
    config_path.write_text(config_template, encoding="utf-8")
    for folder in (Path("artifacts"), Path("runs")):
        folder.mkdir(parents=True, exist_ok=True)
    gitignore = Path(".gitignore")
    lines = []
    if gitignore.exists():
        lines = gitignore.read_text(encoding="utf-8").splitlines()
    for entry in ["artifacts/", "runs/", "*.sqlite", "*.faiss", "*.meta.json"]:
        if entry not in lines:
            lines.append(entry)
    gitignore.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _emit(ctx, {"status": "initialized", "config": str(config_path)})


@app.command()
@no_type_check
def capabilities(ctx: typer.Context) -> None:
    _emit(ctx, VectorExecutionEngine().capabilities())


@app.command()
@no_type_check
def audit(
    ctx: typer.Context,
    vector_store: str | None = typer.Option(None, "--vector-store"),
    vector_store_uri: str | None = typer.Option(None, "--vector-store-uri"),
) -> None:
    base_config = _load_config(ctx.obj.config_path) if ctx.obj else None
    config = _build_config(
        vector_store=vector_store,
        vector_store_uri=vector_store_uri,
        base_config=base_config,
    )
    engine = VectorExecutionEngine(config=config)
    caps = engine.capabilities()
    nd_caps = caps.get("ann", {})
    payload = {
        "determinism_guarantees": {
            "exact": "bit-identical when deterministic contract is used",
            "enforced": True,
        },
        "nd_guarantees": {
            "runner": nd_caps.get("default_runner"),
            "supports_seed": nd_caps.get("supports_seed"),
            "quality_metrics_required": True,
            "replay_strict": True,
        },
        "backend_trust": {
            "vector_store": caps.get("vector_store", {}).get("selected"),
            "backend": caps.get("execution", {}).get("backend"),
        },
        "known_limitations": (
            "ND quality is bounded by ANN candidate quality",
            "Benchmarks require explicit baselines on target hardware",
        ),
    }
    _emit(ctx, payload)


@app.command()
@no_type_check
def ingest(
    ctx: typer.Context,
    doc: str = typer.Option(..., "--doc"),
    vector: str | None = typer.Option(None, "--vector"),
    embed_model: str | None = typer.Option(None, "--embed-model"),
    embed_provider: str | None = typer.Option(None, "--embed-provider"),
    cache_embeddings: str | None = typer.Option(None, "--cache-embeddings"),
    vector_store: str | None = typer.Option(None, "--vector-store"),
    vector_store_uri: str | None = typer.Option(None, "--vector-store-uri"),
    correlation_id: str | None = typer.Option(None, "--correlation-id"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    try:
        resolved_correlation_id = _resolve_correlation_id(correlation_id)
        base_config = _load_config(ctx.obj.config_path) if ctx.obj else None
        req = IngestRequest(
            documents=[doc],
            vectors=[json.loads(vector)] if vector else None,
            embed_model=embed_model,
            embed_provider=embed_provider,
            cache_embeddings=cache_embeddings,
            correlation_id=resolved_correlation_id,
            vector_store=vector_store,
            vector_store_uri=vector_store_uri,
        )
        config = _build_config(
            vector_store=vector_store,
            vector_store_uri=vector_store_uri,
            embed_model=embed_model,
            embed_provider=embed_provider,
            cache_embeddings=cache_embeddings,
            base_config=base_config,
        )
        if dry_run:
            output = {
                "resolved_config": _config_to_dict(config),
                "determinism": "deterministic"
                if config.vector_store is None
                else "deterministic_with_vector_store",
                "provenance_fields": [
                    "vector_store_backend",
                    "vector_store_uri_redacted",
                    "vector_store_index_params",
                ]
                if config.vector_store
                else [],
            }
            _emit(ctx, output)
            return
        engine = VectorExecutionEngine(config=config)
        result = engine.ingest(req)
        _emit(ctx, result)
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


@app.command()
@no_type_check
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
            if len(dims) > 1:
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


@app.command()
@no_type_check
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


@app.command()
@no_type_check
def materialize(
    ctx: typer.Context,
    execution_contract: str = typer.Option(
        ...,
        "--execution-contract",
        help="Execution contract (deterministic warns: non_deterministic loses replay guarantees)",
    ),
    index_mode: str = typer.Option(
        "exact", "--index-mode", help="Index mode: exact|ann"
    ),
    vector_store: str | None = typer.Option(None, "--vector-store"),
    vector_store_uri: str | None = typer.Option(None, "--vector-store-uri"),
) -> None:
    try:
        contract = _parse_contract(execution_contract)
        base_config = _load_config(ctx.obj.config_path) if ctx.obj else None
        engine = VectorExecutionEngine(
            config=_build_config(
                vector_store=vector_store,
                vector_store_uri=vector_store_uri,
                base_config=base_config,
            )
        )
        result = engine.materialize(
            ExecutionArtifactRequest(
                execution_contract=contract,
                index_mode=index_mode,
                vector_store=vector_store,
                vector_store_uri=vector_store_uri,
            )
        )
        _emit(ctx, result)
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


@app.command()
@no_type_check
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
        vector_parsed = json.loads(vector) if vector else None
        contract = _parse_contract(execution_contract)
        intent = _parse_intent(execution_intent)
        mode = _parse_mode(execution_mode)
        sources = (
            [s.strip() for s in randomness_sources.split(",")]
            if randomness_sources
            else None
        )
        req = ExecutionRequestPayload(
            request_text=request_text,
            vector=tuple(vector_parsed) if vector_parsed else None,
            top_k=top_k,
            artifact_id=artifact_id,
            execution_contract=contract,
            execution_intent=intent,
            execution_mode=mode,
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
            correlation_id=resolved_correlation_id,
            vector_store=vector_store,
            vector_store_uri=vector_store_uri,
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
            _emit(
                ctx,
                {"result": result, "explain": explain_result},
            )
            return
        _emit(ctx, result)
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


@app.command()
@no_type_check
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


@app.command()
@no_type_check
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
        sources = (
            [s.strip() for s in randomness_sources.split(",")]
            if randomness_sources
            else None
        )
        randomness_profile = RandomnessProfile(
            seed=randomness_seed,
            sources=tuple(sources or ()),
            bounded=randomness_bounded,
            non_replayable=randomness_non_replayable,
        )
        execution_budget = ExecutionBudget(
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


@app.command()
@no_type_check
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
        if run_a or run_b or bundle_a or bundle_b:
            if not (run_a and run_b) and not (bundle_a and bundle_b):
                raise ValidationError(
                    message="compare requires both --run-a/--run-b or both --bundle-a/--bundle-b"
                )
            if run_a and run_b:
                rec_a = RunStore().load(run_a)
                rec_b = RunStore().load(run_b)
                results_a = rec_a.result.get("results", []) if rec_a.result else []
                results_b = rec_b.result.get("results", []) if rec_b.result else []
                meta_a = rec_a.metadata
                meta_b = rec_b.metadata
            else:
                bundle_a_data = _load_bundle(bundle_a)
                bundle_b_data = _load_bundle(bundle_b)
                results_a = bundle_a_data["result"].get("results", [])
                results_b = bundle_b_data["result"].get("results", [])
                meta_a = bundle_a_data["metadata"]
                meta_b = bundle_b_data["metadata"]
            set_a = set(results_a)
            set_b = set(results_b)
            overlap = set_a & set_b
            union = set_a | set_b
            overlap_ratio = len(overlap) / len(union) if union else 1.0
            recall_delta = (len(overlap) / len(set_a) if set_a else 1.0) - (
                len(overlap) / len(set_b) if set_b else 1.0
            )
            output = {
                "execution_a": meta_a.get("execution_id"),
                "execution_b": meta_b.get("execution_id"),
                "overlap_ratio": overlap_ratio,
                "recall_delta": recall_delta,
                "execution_contract_diff": {
                    "a": meta_a.get("request", {}).get("execution_contract"),
                    "b": meta_b.get("request", {}).get("execution_contract"),
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
            _emit(ctx, output)
            return
        if vector is None:
            raise ValidationError(message="--vector required for artifact comparison")
        intent = _parse_intent(execution_intent)
        contract = _parse_contract(execution_contract)
        payload = ExecutionRequestPayload(
            request_text=None,
            vector=tuple(json.loads(vector)),
            top_k=top_k,
            execution_contract=contract,
            execution_intent=intent,
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


@vdb_app.command("status")
@no_type_check
def vdb_status(
    ctx: typer.Context,
    vector_store: str = typer.Option(..., "--vector-store"),
    uri: str | None = typer.Option(None, "--uri"),
) -> None:
    try:
        engine = VectorExecutionEngine(
            config=_build_config(vector_store=vector_store, vector_store_uri=uri)
        )
        adapter = engine.vector_store_resolution.adapter
        status = {
            "backend": engine.vector_store_resolution.descriptor.name,
            "reachable": True,
            "version": engine.vector_store_resolution.descriptor.version,
            "uri_redacted": engine.vector_store_resolution.uri_redacted,
        }
        if hasattr(adapter, "status"):
            status.update(adapter.status())
        ann_runner = getattr(engine.backend, "ann", None)
        if ann_runner is not None and hasattr(ann_runner, "index_info"):
            status["ann_index"] = ann_runner.index_info(engine.default_artifact_id)
        _emit(ctx, status)
    except BijuxError as exc:
        record_failure(exc)
        payload = {"backend": vector_store, "reachable": False}
        if is_refusal(exc):
            payload["error"] = refusal_payload(exc)
        else:
            payload["error"] = {"message": str(exc)}
        _emit(ctx, payload)
    except Exception:  # pragma: no cover
        sys.exit(1)


@vdb_app.command("rebuild")
@no_type_check
def vdb_rebuild(
    ctx: typer.Context,
    vector_store: str = typer.Option(..., "--vector-store"),
    uri: str | None = typer.Option(None, "--uri"),
    mode: str = typer.Option("exact", "--mode", help="exact|ann"),
) -> None:
    try:
        engine = VectorExecutionEngine(
            config=_build_config(vector_store=vector_store, vector_store_uri=uri)
        )
        index_type = "exact" if mode == "exact" else "ann"
        if index_type == "ann":
            ann_runner = getattr(engine.backend, "ann", None)
            if ann_runner is None:
                raise ValidationError(
                    message="Selected backend does not support ANN rebuild"
                )
            artifact = engine.stores.ledger.get_artifact(engine.default_artifact_id)
            if artifact is None:
                raise ValidationError(message="No artifact available for ANN rebuild")
            vectors = list(engine.stores.vectors.list_vectors())
            index_info = ann_runner.build_index(
                artifact.artifact_id, vectors, artifact.metric, None
            )
            index_hash = index_info.get("index_hash") if index_info else None
            extra = (("ann_index_info", json.dumps(index_info, sort_keys=True)),)
            if index_hash:
                extra = extra + (("ann_index_hash", str(index_hash)),)
            updated = replace(
                artifact,
                build_params=artifact.build_params + extra,
                index_state="ready",
            )
            with engine._tx() as tx:
                engine.stores.ledger.put_artifact(tx, updated)
            _emit(ctx, {"status": "rebuilt", "ann_index": index_info})
            return
        adapter = engine.vector_store_resolution.adapter
        if not hasattr(adapter, "rebuild"):
            raise ValidationError(
                message="Selected vector store does not support rebuild"
            )
        status = adapter.rebuild(index_type=index_type)
        _emit(ctx, status)
    except BijuxError as exc:
        record_failure(exc)
        payload = {"backend": vector_store, "reachable": False}
        if is_refusal(exc):
            payload["error"] = refusal_payload(exc)
        else:
            payload["error"] = {"message": str(exc)}
        _emit(ctx, payload)
    except Exception:  # pragma: no cover
        sys.exit(1)


@vdb_app.command("compact")
@no_type_check
def vdb_compact(
    ctx: typer.Context,
    vector_store: str = typer.Option(..., "--vector-store"),
    uri: str | None = typer.Option(None, "--uri"),
    mode: str = typer.Option("ann", "--mode", help="exact|ann"),
) -> None:
    try:
        engine = VectorExecutionEngine(
            config=_build_config(vector_store=vector_store, vector_store_uri=uri)
        )
        index_type = "exact" if mode == "exact" else "ann"
        if index_type == "ann":
            ann_runner = getattr(engine.backend, "ann", None)
            if ann_runner is None or not getattr(
                ann_runner, "supports_compaction", False
            ):
                raise ValidationError(
                    message="Selected backend does not support ANN compaction"
                )
            artifact = engine.stores.ledger.get_artifact(engine.default_artifact_id)
            if artifact is None:
                raise ValidationError(
                    message="No artifact available for ANN compaction"
                )
            vectors = list(engine.stores.vectors.list_vectors())
            ann_runner.compact(artifact.artifact_id, vectors, artifact.metric)
            _emit(ctx, {"status": "compacted", "backend": vector_store})
            return
        adapter = engine.vector_store_resolution.adapter
        if not hasattr(adapter, "compact"):
            raise ValidationError(
                message="Selected vector store does not support compaction"
            )
        status = adapter.compact(index_type=index_type)
        _emit(ctx, status)
    except BijuxError as exc:
        record_failure(exc)
        payload = {"backend": vector_store, "reachable": False}
        if is_refusal(exc):
            payload["error"] = refusal_payload(exc)
        else:
            payload["error"] = {"message": str(exc)}
        _emit(ctx, payload)
    except Exception:  # pragma: no cover
        sys.exit(1)


@nd_app.command("tune")
@no_type_check
def nd_tune(
    ctx: typer.Context,
    vector_store: str = typer.Option("memory", "--vector-store"),
    uri: str | None = typer.Option(None, "--uri"),
    top_k: int = typer.Option(10, "--top-k"),
    samples: int = typer.Option(10, "--samples"),
    cache: Path | None = ND_TUNE_CACHE_OPTION,
    dataset_dir: Path | None = ND_TUNE_DATASET_DIR_OPTION,
    size: int = typer.Option(1000, "--size"),
    dimension: int = typer.Option(DEFAULT_DIMENSION, "--dimension"),
    query_count: int = typer.Option(DEFAULT_QUERY_COUNT, "--query-count"),
    seed: int = typer.Option(DEFAULT_SEED, "--seed"),
    use_existing: bool = typer.Option(
        False,
        "--use-existing",
        help="Use existing store vectors instead of loading dataset",
    ),
) -> None:
    try:
        engine = VectorExecutionEngine(
            config=_build_config(vector_store=vector_store, vector_store_uri=uri)
        )
        ann_runner = getattr(engine.backend, "ann", None)
        if ann_runner is None:
            raise ValidationError(message="ANN runner required for tuning")
        artifact = engine.stores.ledger.get_artifact(engine.default_artifact_id)
        if artifact is None:
            raise ValidationError(message="No artifact available for tuning")
        vectors = list(engine.stores.vectors.list_vectors())
        queries: list[tuple[float, ...]] = []
        if dataset_dir and not use_existing:
            folder = dataset_folder(Path(dataset_dir), size, dimension, seed)
            if not folder.exists():
                dataset = generate_dataset(
                    size=size,
                    dimension=dimension,
                    query_count=query_count,
                    seed=seed,
                )
                save_dataset(dataset, folder)
            dataset = load_dataset(folder)
            engine.ingest(
                IngestRequest(
                    documents=dataset.documents,
                    vectors=dataset.vectors.tolist(),
                )
            )
            vectors = list(engine.stores.vectors.list_vectors())
            queries = [tuple(q.tolist()) for q in dataset.queries[: max(1, samples)]]
        if not vectors:
            raise ValidationError(message="No vectors available for tuning")
        if not queries:
            queries = [tuple(v.values) for v in vectors[: max(1, samples)]]
        dim = vectors[0].dimension
        cache_key = fingerprint(
            {
                "vector_fingerprint": artifact.vector_fingerprint,
                "metric": artifact.metric,
                "dimension": dim,
                "runner": ann_runner.__class__.__name__,
                "runner_version": getattr(ann_runner, "__version__", "unknown"),
                "top_k": top_k,
                "samples": samples,
                "dataset": {
                    "dir": str(dataset_dir) if dataset_dir else None,
                    "size": size,
                    "dimension": dimension,
                    "query_count": query_count,
                    "seed": seed,
                    "use_existing": use_existing,
                },
            }
        )
        if cache is not None and cache.exists():
            cached = json.loads(cache.read_text(encoding="utf-8"))
            if cached.get("cache_key") == cache_key:
                _emit(ctx, cached["payload"])
                return

        def _exact(query: tuple[float, ...]) -> list[Result]:
            scored: list[Result] = []
            for vector in vectors:
                score = scoring.score(artifact.metric, query, tuple(vector.values))
                scored.append(
                    Result(
                        request_id="nd-tune",
                        document_id="",
                        chunk_id=vector.chunk_id,
                        vector_id=vector.vector_id,
                        artifact_id=artifact.artifact_id,
                        score=score,
                        rank=0,
                    )
                )
            scored.sort(key=scoring.tie_break_key)
            return scored[:top_k]

        exact_cache = {query: _exact(query) for query in queries}
        grid = {
            "m": [8, 16, 32],
            "ef_construction": [100, 200],
            "ef_search": [50, 100, 200],
        }
        results: list[dict[str, object]] = []
        for m_val in grid["m"]:
            for efc in grid["ef_construction"]:
                for efs in grid["ef_search"]:
                    nd_settings = NDSettings(
                        profile=None,
                        m=m_val,
                        ef_construction=efc,
                        ef_search=efs,
                        build_on_demand=True,
                    )
                    ann_runner.build_index(
                        artifact.artifact_id, vectors, artifact.metric, nd_settings
                    )
                    request = ExecutionRequest(
                        request_id=f"nd-tune-m{m_val}-efc{efc}-efs{efs}",
                        text=None,
                        vector=queries[0],
                        top_k=top_k,
                        execution_contract=ExecutionContract.NON_DETERMINISTIC,
                        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
                        execution_mode=ExecutionMode.BOUNDED,
                        nd_settings=nd_settings,
                    )
                    latencies: list[float] = []
                    overlaps: list[float] = []
                    instabilities: list[float] = []
                    for query in queries:
                        start = time.perf_counter()
                        ann_results = list(
                            ann_runner.approximate_request(
                                artifact,
                                replace(request, vector=query),
                            )
                        )
                        latencies.append((time.perf_counter() - start) * 1000)
                        exact_results = exact_cache[query]
                        ids_ann = [r.vector_id for r in ann_results]
                        ids_exact = [r.vector_id for r in exact_results]
                        overlap = set(ids_ann) & set(ids_exact)
                        overlaps.append(len(overlap) / float(len(ids_exact) or 1))
                        instabilities.append(
                            _rank_instability(ids_ann, ids_exact, overlap)
                        )
                    p95 = (
                        sorted(latencies)[int(len(latencies) * 0.95) - 1]
                        if latencies
                        else 0.0
                    )
                    result = {
                        "params": {
                            "m": m_val,
                            "ef_construction": efc,
                            "ef_search": efs,
                        },
                        "latency_ms": {
                            "mean": round(mean(latencies), 3) if latencies else 0.0,
                            "p95": round(p95, 3),
                        },
                        "quality": {
                            "overlap_at_k": round(mean(overlaps), 4)
                            if overlaps
                            else 0.0,
                            "rank_instability": round(mean(instabilities), 4)
                            if instabilities
                            else 0.0,
                        },
                        "samples": len(latencies),
                    }
                    results.append(result)

        def _dominates(a: dict[str, object], b: dict[str, object]) -> bool:
            a_lat = a["latency_ms"]["mean"]
            b_lat = b["latency_ms"]["mean"]
            a_qual = a["quality"]["overlap_at_k"]
            b_qual = b["quality"]["overlap_at_k"]
            return (a_lat <= b_lat and a_qual >= b_qual) and (
                a_lat < b_lat or a_qual > b_qual
            )

        pareto = []
        for candidate in results:
            if any(
                _dominates(other, candidate)
                for other in results
                if other is not candidate
            ):
                continue
            pareto.append(candidate)

        recommended = max(
            results,
            key=lambda r: (r["quality"]["overlap_at_k"], -r["latency_ms"]["mean"]),
        )
        params = recommended["params"]
        config_snippet = "\n".join(
            [
                "[nd]",
                f"m = {params['m']}",
                f"ef_construction = {params['ef_construction']}",
                f"ef_search = {params['ef_search']}",
                "two_stage = true",
            ]
        )
        payload = {
            "grid": results,
            "pareto_frontier": pareto,
            "recommended": recommended,
            "config_snippet": config_snippet,
        }
        if cache is not None:
            cache_payload = {"cache_key": cache_key, "payload": payload}
            cache.write_text(json.dumps(cache_payload, indent=2), encoding="utf-8")
        _emit(ctx, payload)
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


@artifact_app.command("pack")
@no_type_check
def artifact_pack(
    ctx: typer.Context,
    run_id: str = typer.Argument(...),
    out: Path = typer.Option(Path("bundle.zip"), "--out"),  # noqa: B008
    include_vectors: bool = typer.Option(False, "--include-vectors"),
) -> None:
    try:
        run = RunStore().load(run_id)
        base_config = _load_config(ctx.obj.config_path) if ctx.obj else None
        config_payload = _redact_config(base_config)
        engine = VectorExecutionEngine()
        vectors_payload: dict[str, object] = {}
        if include_vectors:
            vectors_payload["vectors"] = []
            for vid in run.result.get("results", []) if run.result else []:
                vec = engine.stores.vectors.get_vector(vid)
                if vec:
                    vectors_payload["vectors"].append(
                        {"vector_id": vid, "values": list(vec.values)}
                    )
        vector_hashes = []
        for vid in run.result.get("results", []) if run.result else []:
            vec = engine.stores.vectors.get_vector(vid)
            if vec:
                vector_hashes.append(
                    {"vector_id": vid, "hash": fingerprint(vec.values)}
                )
        bundle = {
            "metadata": run.metadata,
            "result": run.result or {},
            "config": config_payload,
            "vector_hashes": vector_hashes,
        }
        with zipfile.ZipFile(out, "w") as zf:
            zf.writestr("metadata.json", json.dumps(bundle["metadata"], indent=2))
            zf.writestr("result.json", json.dumps(bundle["result"], indent=2))
            zf.writestr("config.json", json.dumps(bundle["config"], indent=2))
            zf.writestr(
                "vector_hashes.json", json.dumps(bundle["vector_hashes"], indent=2)
            )
            if include_vectors:
                zf.writestr("vectors.json", json.dumps(vectors_payload, indent=2))
        _emit(ctx, {"status": "packed", "bundle": str(out)})
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


@artifact_app.command("unpack")
@no_type_check
def artifact_unpack(
    ctx: typer.Context,
    bundle: Path = typer.Argument(...),  # noqa: B008
    out_dir: Path = typer.Option(Path("bundle_out"), "--out-dir"),  # noqa: B008
) -> None:
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(bundle, "r") as zf:
            zf.extractall(out_dir)
        _emit(ctx, {"status": "unpacked", "path": str(out_dir)})
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


@app.command()
@no_type_check
def bench(
    ctx: typer.Context,
    size: int = typer.Option(1000, "--size", help="Dataset size (1k/10k/100k)"),
    mode: str = typer.Option("exact", "--mode", help="exact|ann"),
    store: str = typer.Option("memory", "--store", help="memory|vdb"),
    vector_store: str | None = typer.Option(None, "--vector-store"),
    vector_store_uri: str | None = typer.Option(None, "--vector-store-uri"),
    repeats: int = typer.Option(3, "--repeats"),
    warmup: int = typer.Option(1, "--warmup"),
    seed: int = typer.Option(DEFAULT_SEED, "--seed"),
    dimension: int = typer.Option(DEFAULT_DIMENSION, "--dimension"),
    query_count: int = typer.Option(DEFAULT_QUERY_COUNT, "--query-count"),
    dataset_dir: Path = typer.Option(  # noqa: B008
        Path("benchmarks/artifacts"), "--dataset-dir"
    ),
    baseline: Path | None = typer.Option(None, "--baseline"),  # noqa: B008
    fail_on_regression: bool = typer.Option(False, "--fail-on-regression"),
    regress_threshold: float = typer.Option(0.2, "--regress-threshold"),
    overlap_regress_threshold: float = typer.Option(
        0.05, "--overlap-regress-threshold"
    ),
) -> None:
    try:
        if store not in {"memory", "vdb"}:
            typer.echo("store must be memory|vdb")
            sys.exit(1)
        backend = None
        if store == "vdb":
            backend = vector_store or "faiss"
        base = dataset_dir
        folder = dataset_folder(base, size, dimension, seed)
        if not folder.exists():
            dataset = generate_dataset(
                size=size, dimension=dimension, query_count=query_count, seed=seed
            )
            save_dataset(dataset, folder)
        dataset = load_dataset(folder)
        result = run_benchmark(
            documents=dataset.documents,
            vectors=dataset.vectors,
            queries=dataset.queries,
            store_backend=backend,
            store_uri=vector_store_uri,
            mode=mode,
            top_k=5,
            repeats=repeats,
            warmup=warmup,
        )
        table = format_table(result["summary"])
        if baseline:
            baseline_payload = json.loads(baseline.read_text(encoding="utf-8"))
            base_summary = baseline_payload.get("summary", {})
            if base_summary:
                slowdown = (
                    result["summary"]["mean_ms"] / base_summary.get("mean_ms", 1.0)
                ) - 1.0
                result["regression"] = {
                    "slowdown_pct": slowdown * 100.0,
                    "threshold_pct": regress_threshold * 100.0,
                    "regressed": slowdown > regress_threshold,
                }
                if "quality" in result and "quality" in baseline_payload:
                    base_quality = baseline_payload.get("quality", {})
                    if base_quality:
                        overlap_delta = base_quality.get("overlap_at_k", 1.0) - result[
                            "quality"
                        ].get("overlap_at_k", 1.0)
                        result["regression"]["overlap_drop"] = overlap_delta
                        result["regression"]["overlap_threshold"] = (
                            overlap_regress_threshold
                        )
                        result["regression"]["overlap_regressed"] = (
                            overlap_delta > overlap_regress_threshold
                        )
                if slowdown > regress_threshold and fail_on_regression:
                    _emit(ctx, result, table=table)
                    sys.exit(2)
        _emit(ctx, result, table=table)
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


@config_app.command("show")
@no_type_check
def config_show(ctx: typer.Context) -> None:
    try:
        config = _load_config(ctx.obj.config_path) if ctx.obj else None
        _emit(ctx, _redact_config(config))
    except Exception:  # pragma: no cover
        sys.exit(1)


@app.command("metrics")
@no_type_check
def metrics_snapshot(ctx: typer.Context) -> None:
    try:
        snapshot = METRICS.snapshot()
        _emit(
            ctx,
            {"counters": snapshot.counters, "timers_ms": snapshot.timers_ms},
        )
    except Exception:  # pragma: no cover
        sys.exit(1)


@app.command("debug-bundle")
@no_type_check
def debug_bundle(
    ctx: typer.Context,
    include_provenance: bool = typer.Option(False, "--include-provenance"),
    vector_store: str | None = typer.Option(None, "--vector-store"),
    vector_store_uri: str | None = typer.Option(None, "--vector-store-uri"),
) -> None:
    try:
        base_config = _load_config(ctx.obj.config_path) if ctx.obj else None
        config = _build_config(
            vector_store=vector_store,
            vector_store_uri=vector_store_uri,
            base_config=base_config,
        )
        engine = VectorExecutionEngine(config=config)
        status = {
            "backend": engine.vector_store_resolution.descriptor.name,
            "reachable": True,
            "version": engine.vector_store_resolution.descriptor.version,
            "uri_redacted": engine.vector_store_resolution.uri_redacted,
        }
        adapter = engine.vector_store_resolution.adapter
        if hasattr(adapter, "status"):
            status.update(adapter.status())
        bundle: dict[str, object] = {
            "config": _redact_config(config),
            "capabilities": engine.capabilities(),
            "vector_store_status": status,
            "metrics": METRICS.snapshot().__dict__,
        }
        if include_provenance:
            artifacts = tuple(engine.stores.ledger.list_artifacts())
            latest_exec: dict[str, str] = {}
            for artifact in artifacts:
                stored = engine.stores.ledger.latest_execution_result(
                    artifact.artifact_id
                )
                if stored is not None:
                    latest_exec[artifact.artifact_id] = stored.execution_id
            bundle["provenance"] = {
                "artifacts": [a.artifact_id for a in artifacts],
                "latest_execution_ids": latest_exec,
            }
        _emit(ctx, bundle)
    except BijuxError as exc:
        record_failure(exc)
        if is_refusal(exc):
            _emit(ctx, {"error": refusal_payload(exc)})
        sys.exit(to_cli_exit(exc))
    except Exception:  # pragma: no cover
        sys.exit(1)


if __name__ == "__main__":
    app()
