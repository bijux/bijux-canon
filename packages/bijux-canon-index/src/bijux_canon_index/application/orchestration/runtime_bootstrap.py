# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Runtime bootstrap helpers for the orchestration layer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading
from typing import Any

from bijux_canon_index.contracts.authz import AllowAllAuthz, Authz, DenyAllAuthz
from bijux_canon_index.core.config import ExecutionConfig, VectorStoreConfig
from bijux_canon_index.core.identity.policies import (
    ContentAddressedIdPolicy,
    IdGenerationStrategy,
)
from bijux_canon_index.infra.adapters.sqlite.backend import sqlite_backend
from bijux_canon_index.infra.adapters.vectorstore_registry import VECTOR_STORES
from bijux_canon_index.infra.adapters.vectorstore_source import VectorStoreVectorSource
from bijux_canon_index.infra.environment import read_env
from bijux_canon_index.infra.logging import log_event
from bijux_canon_index.infra.runtime_paths import default_state_path, ensure_parent_dir

_BACKEND_POOL: dict[tuple[str, str], Any] = {}
_BACKEND_LOCK = threading.Lock()


@dataclass(frozen=True)
class OrchestratorRuntimeBootstrap:
    backend: Any
    authz: Authz
    stores: Any
    vector_store_enabled: bool
    vector_store_resolution: Any
    read_only: bool
    id_policy: IdGenerationStrategy
    default_artifact_id: str
    nd_rate_limit: int
    nd_rate_window_seconds: int
    nd_circuit_max_failures: int
    nd_circuit_cooldown_s: int


def resolve_backend(backend_env: str, chosen_path: Path) -> Any:
    if backend_env == "memory":
        from bijux_canon_index.infra.adapters.memory.backend import memory_backend

        return memory_backend()
    normalized_path = ensure_parent_dir(chosen_path)
    key = (backend_env or "", str(normalized_path))
    with _BACKEND_LOCK:
        cached = _BACKEND_POOL.get(key)
        if cached is not None:
            return cached
        backend: Any
        if backend_env == "hnsw":
            from bijux_canon_index.infra.adapters.hnsw.backend import hnsw_backend

            backend = hnsw_backend(
                db_path=str(normalized_path),
                index_dir=read_env(
                    "BIJUX_CANON_INDEX_HNSW_PATH",
                    legacy="BIJUX_VEX_HNSW_PATH",
                ),
            )
        else:
            backend = sqlite_backend(str(normalized_path))
        _BACKEND_POOL[key] = backend
        return backend


def bootstrap_runtime(
    *,
    backend: Any | None,
    authz: Authz | None,
    state_path: str | Path | None,
    config: ExecutionConfig,
) -> OrchestratorRuntimeBootstrap:
    runtime_backend = backend or _resolve_backend_from_env(state_path)
    vector_store_enabled = config.vector_store is not None
    vector_store_cfg = config.vector_store or VectorStoreConfig(backend="memory")
    vector_store_resolution = VECTOR_STORES.resolve(
        vector_store_cfg.backend or "memory",
        uri=vector_store_cfg.uri,
        options=vector_store_cfg.options,
    )
    log_event(
        "backend_selected",
        backend=getattr(runtime_backend, "name", "unknown"),
        vector_store=vector_store_resolution.descriptor.name,
    )
    stores = runtime_backend.stores
    if vector_store_enabled:
        stores = runtime_backend.stores._replace(
            vectors=VectorStoreVectorSource(
                runtime_backend.stores.vectors, vector_store_resolution
            )
        )
    id_policy = ContentAddressedIdPolicy()
    return OrchestratorRuntimeBootstrap(
        backend=runtime_backend,
        authz=authz or _resolve_authz_from_env(),
        stores=stores,
        vector_store_enabled=vector_store_enabled,
        vector_store_resolution=vector_store_resolution,
        read_only=_resolve_read_only_from_env(),
        id_policy=id_policy,
        default_artifact_id=id_policy.next_artifact_id(),
        nd_rate_limit=_read_int_env(
            "BIJUX_CANON_INDEX_ND_RATE_LIMIT",
            legacy="BIJUX_VEX_ND_RATE_LIMIT",
            default="0",
        ),
        nd_rate_window_seconds=_read_int_env(
            "BIJUX_CANON_INDEX_ND_RATE_WINDOW_S",
            legacy="BIJUX_VEX_ND_RATE_WINDOW_S",
            default="60",
        ),
        nd_circuit_max_failures=_read_int_env(
            "BIJUX_CANON_INDEX_ND_CIRCUIT_MAX_FAILURES",
            legacy="BIJUX_VEX_ND_CIRCUIT_MAX_FAILURES",
            default="3",
        ),
        nd_circuit_cooldown_s=_read_int_env(
            "BIJUX_CANON_INDEX_ND_CIRCUIT_COOLDOWN_S",
            legacy="BIJUX_VEX_ND_CIRCUIT_COOLDOWN_S",
            default="30",
        ),
    )


def _resolve_backend_from_env(state_path: str | Path | None) -> Any:
    backend_env = (
        read_env(
            "BIJUX_CANON_INDEX_BACKEND",
            legacy="BIJUX_VEX_BACKEND",
            default="",
        )
        or ""
    ).lower()
    chosen_raw: str | Path = (
        state_path
        or read_env(
            "BIJUX_CANON_INDEX_STATE_PATH",
            legacy="BIJUX_VEX_STATE_PATH",
            default=str(default_state_path()),
        )
        or str(default_state_path())
    )
    return resolve_backend(backend_env, Path(chosen_raw))


def _resolve_authz_from_env() -> Authz:
    auth_mode = (
        read_env(
            "BIJUX_CANON_INDEX_AUTHZ_MODE",
            legacy="BIJUX_VEX_AUTHZ_MODE",
            default="",
        )
        or ""
    ).lower()
    return DenyAllAuthz() if auth_mode in {"deny", "deny_all"} else AllowAllAuthz()


def _resolve_read_only_from_env() -> bool:
    read_only = (
        read_env(
            "BIJUX_CANON_INDEX_READ_ONLY",
            legacy="BIJUX_VEX_READ_ONLY",
            default="",
        )
        or ""
    ).lower()
    return read_only in {"1", "true", "yes"}


def _read_int_env(name: str, *, legacy: str, default: str) -> int:
    return int(read_env(name, legacy=legacy, default=default) or default)


__all__ = ["OrchestratorRuntimeBootstrap", "bootstrap_runtime", "resolve_backend"]
