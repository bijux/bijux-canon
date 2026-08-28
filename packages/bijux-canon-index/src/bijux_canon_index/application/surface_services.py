# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Application services shared by index HTTP and command transports."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
import zipfile

from bijux_canon_index.application.engine import VectorExecutionEngine
from bijux_canon_index.application.index_audit import IndexCompatibility
from bijux_canon_index.application.index_service import IndexService
from bijux_canon_index.core.config import ExecutionConfig
from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.errors import ValidationError
from bijux_canon_index.core.identity.ids import fingerprint
from bijux_canon_index.infra.adapters.vectorstore_registry import VECTOR_STORES
from bijux_canon_index.infra.embeddings.registry import EMBEDDING_PROVIDERS
from bijux_canon_index.infra.logging import enable_trace, trace_events
from bijux_canon_index.infra.metrics import METRICS
from bijux_canon_index.infra.run_store import RunStore
from bijux_canon_index.infra.runtime_paths import default_generation_registry_path


def index_service_from_environment(
    *,
    registry_root: str | Path | None = None,
) -> IndexService:
    """Compose the canonical generation service from operator configuration."""

    root = Path(
        registry_root
        or os.getenv("BIJUX_CANON_INDEX_GENERATION_ROOT")
        or default_generation_registry_path()
    )
    model_lock_artifact_id = os.getenv("BIJUX_CANON_INDEX_MODEL_LOCK_ARTIFACT_ID")
    raw_dimension = os.getenv("BIJUX_CANON_INDEX_MODEL_DIMENSION")
    configuration_id = os.getenv("BIJUX_CANON_INDEX_CONFIGURATION_ID")
    if (model_lock_artifact_id is None) != (raw_dimension is None):
        raise ValueError(
            "generation compatibility requires both model lock and dimension"
        )
    if configuration_id is not None and model_lock_artifact_id is None:
        raise ValueError(
            "generation configuration compatibility requires a model profile"
        )
    compatibility = (
        None
        if model_lock_artifact_id is None
        else IndexCompatibility(
            model_lock_artifact_id,
            int(raw_dimension or ""),
            configuration_id=configuration_id,
        )
    )
    return IndexService(root, compatibility=compatibility)


def list_execution_runs(*, limit: int | None, offset: int) -> list[str]:
    """List persisted execution identifiers."""
    return RunStore().list_runs(limit=limit, offset=offset)


def load_execution_run(run_id: str) -> Any:
    """Load one persisted execution record."""
    return RunStore().load(run_id)


def vector_store_name(config: ExecutionConfig) -> str | None:
    """Resolve the configured vector-store descriptor name without opening a store."""
    if config.vector_store is None:
        return None
    name = config.vector_store.backend
    descriptor = next(
        (item for item in VECTOR_STORES.descriptors() if item.name == name), None
    )
    return descriptor.name if descriptor is not None else None


def validate_vector_store(
    *, config: ExecutionConfig, contract: ExecutionContract | None
) -> None:
    """Resolve a configured vector store and enforce its execution contract."""
    if config.vector_store is None:
        return
    resolution = VECTOR_STORES.resolve(
        config.vector_store.backend or "memory",
        uri=config.vector_store.uri,
        options=config.vector_store.options,
    )
    if (
        contract is ExecutionContract.DETERMINISTIC
        and not resolution.descriptor.deterministic_exact
    ):
        raise ValidationError(
            message="deterministic contract requires deterministic vector store"
        )
    if (
        contract is ExecutionContract.NON_DETERMINISTIC
        and not resolution.descriptor.supports_ann
    ):
        raise ValidationError(
            message="non_deterministic contract requires ANN-capable vector store"
        )


def environment_report(
    *, config: ExecutionConfig, workspace: Path
) -> dict[str, object]:
    """Inspect optional dependencies, adapters, and writable runtime locations."""
    extras: dict[str, bool] = {}
    for module in ("faiss", "qdrant_client"):
        try:
            __import__(module)
            extras[module] = True
        except Exception:
            extras[module] = False
    backend_status: dict[str, object] = {"configured": False}
    if config.vector_store is not None:
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
        if hasattr(resolution.adapter, "status"):
            backend_status["status"] = resolution.adapter.status()
    run_dir = RunStore()._base
    return {
        "extras": extras,
        "backend": backend_status,
        "embeddings": {
            "providers": EMBEDDING_PROVIDERS.providers(),
            "default": EMBEDDING_PROVIDERS.default,
        },
        "permissions": {
            "workspace_writable": os.access(workspace, os.W_OK),
            "run_dir_writable": os.access(run_dir, os.W_OK)
            if run_dir.exists()
            else True,
        },
    }


def metrics_payload() -> dict[str, object]:
    """Return the current metrics snapshot as transport-neutral data."""
    snapshot = METRICS.snapshot()
    return {"counters": snapshot.counters, "timers_ms": snapshot.timers_ms}


def debug_bundle_payload(
    *,
    engine: VectorExecutionEngine,
    redacted_config: dict[str, object],
    include_provenance: bool,
) -> dict[str, object]:
    """Build the diagnostic bundle owned by the index application."""
    resolution = engine.vector_store_resolution
    status: dict[str, object] = {
        "backend": resolution.descriptor.name,
        "reachable": True,
        "version": resolution.descriptor.version,
        "uri_redacted": resolution.uri_redacted,
    }
    if hasattr(resolution.adapter, "status"):
        status.update(resolution.adapter.status())
    bundle: dict[str, object] = {
        "config": redacted_config,
        "capabilities": engine.capabilities(),
        "vector_store_status": status,
        "metrics": METRICS.snapshot().__dict__,
    }
    if include_provenance:
        artifacts = tuple(engine.stores.ledger.list_artifacts())
        latest_exec: dict[str, str] = {}
        for artifact in artifacts:
            stored = engine.stores.ledger.latest_execution_result(artifact.artifact_id)
            if stored is not None:
                latest_exec[artifact.artifact_id] = stored.execution_id
        bundle["provenance"] = {
            "artifacts": [artifact.artifact_id for artifact in artifacts],
            "latest_execution_ids": latest_exec,
        }
    return bundle


def enable_execution_trace() -> None:
    """Enable in-process index trace collection."""
    enable_trace()


def execution_trace_events() -> list[dict[str, object]]:
    """Return accumulated trace events for response rendering."""
    return trace_events()


def redact_vector_store_uri(config_payload: dict[str, object]) -> dict[str, object]:
    """Redact a configured vector-store URI through its registered adapter."""
    vector_store = config_payload.get("vector_store")
    if isinstance(vector_store, dict) and vector_store.get("uri"):
        resolution = VECTOR_STORES.resolve(
            vector_store.get("backend") or "memory",
            uri=str(vector_store.get("uri")),
        )
        vector_store["uri"] = resolution.uri_redacted
    return config_payload


def pack_execution_artifact(
    *, run_id: str, out: Path, include_vectors: bool, config_payload: dict[str, object]
) -> None:
    """Create a portable bundle from one persisted execution."""
    run = RunStore().load(run_id)
    engine = VectorExecutionEngine()
    vectors_payload: dict[str, object] = {}
    if include_vectors:
        vector_entries: list[dict[str, object]] = []
        vectors_payload["vectors"] = vector_entries
        for vector_id in run.result.get("results", []) if run.result else []:
            vector = engine.stores.vectors.get_vector(vector_id)
            if vector:
                vector_entries.append(
                    {"vector_id": vector_id, "values": list(vector.values)}
                )
    vector_hashes = []
    for vector_id in run.result.get("results", []) if run.result else []:
        vector = engine.stores.vectors.get_vector(vector_id)
        if vector:
            vector_hashes.append(
                {"vector_id": vector_id, "hash": fingerprint(vector.values)}
            )
    bundle = {
        "metadata": run.metadata,
        "result": run.result or {},
        "config": config_payload,
        "vector_hashes": vector_hashes,
    }
    with zipfile.ZipFile(out, "w") as archive:
        for name in ("metadata", "result", "config", "vector_hashes"):
            archive.writestr(f"{name}.json", json.dumps(bundle[name], indent=2))
        if include_vectors:
            archive.writestr("vectors.json", json.dumps(vectors_payload, indent=2))


def unpack_execution_artifact(*, bundle: Path, out_dir: Path) -> None:
    """Extract a portable execution bundle into an operator-selected directory."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(bundle, "r") as archive:
        archive.extractall(out_dir)


__all__ = [
    "debug_bundle_payload",
    "enable_execution_trace",
    "environment_report",
    "execution_trace_events",
    "index_service_from_environment",
    "list_execution_runs",
    "load_execution_run",
    "metrics_payload",
    "pack_execution_artifact",
    "redact_vector_store_uri",
    "unpack_execution_artifact",
    "validate_vector_store",
    "vector_store_name",
]
