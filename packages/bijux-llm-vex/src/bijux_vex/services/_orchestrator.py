# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, cast
import uuid

from bijux_vex.boundaries.pydantic_edges.models import (
    CreateRequest,
    ExecutionArtifactRequest,
    ExecutionRequestPayload,
    ExplainRequest,
    IngestRequest,
)
from bijux_vex.contracts.authz import AllowAllAuthz, Authz, DenyAllAuthz
from bijux_vex.contracts.tx import Tx
from bijux_vex.core.config import ExecutionConfig, VectorStoreConfig
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import (
    AuthzDeniedError,
    BackendUnavailableError,
    BudgetExceededError,
    InvariantError,
    NDExecutionUnavailableError,
    NotFoundError,
    ReplayNotSupportedError,
    ValidationError,
)
from bijux_vex.core.errors.refusal import is_refusal, refusal_payload
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.identity.fingerprints import (
    corpus_fingerprint,
    determinism_fingerprint,
    vectors_fingerprint,
)
from bijux_vex.core.identity.ids import fingerprint
from bijux_vex.core.runtime.execution_plan import ExecutionPlan
from bijux_vex.core.runtime.vector_execution import (
    RandomnessProfile,
    derive_execution_id,
    execution_signature,
)
from bijux_vex.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    ExecutionBudget,
    ExecutionRequest,
    NDSettings,
    Vector,
)
from bijux_vex.domain.execution_requests.compare import compare_executions
from bijux_vex.domain.execution_requests.execute import (
    execute_request,
    start_execution_session,
)
from bijux_vex.domain.nd.model import NDExecutionModel
from bijux_vex.domain.provenance.lineage import explain_result
from bijux_vex.domain.provenance.replay import replay
from bijux_vex.infra.adapters.sqlite.backend import sqlite_backend
from bijux_vex.infra.adapters.vectorstore_registry import VECTOR_STORES
from bijux_vex.infra.adapters.vectorstore_source import VectorStoreVectorSource
from bijux_vex.infra.embeddings.cache import (
    build_cache,
    cache_key,
    embedding_config_hash,
    metadata_as_dict,
)
from bijux_vex.infra.embeddings.registry import EMBEDDING_PROVIDERS
from bijux_vex.infra.logging import log_event
from bijux_vex.infra.metrics import METRICS, timed
from bijux_vex.infra.run_store import RunStore
from bijux_vex.infra.runners.registry import RUNNERS
from bijux_vex.services.policies.id_policy import (
    ContentAddressedIdPolicy,
    IdGenerationStrategy,
)

_BACKEND_POOL: dict[tuple[str, str], Any] = {}
_BACKEND_LOCK = threading.Lock()


def _resolve_backend(backend_env: str, chosen_path: Path) -> Any:
    if backend_env == "memory":
        from bijux_vex.infra.adapters.memory.backend import memory_backend

        return memory_backend()
    key = (backend_env or "", str(chosen_path))
    with _BACKEND_LOCK:
        cached = _BACKEND_POOL.get(key)
        if cached is not None:
            return cached
        backend: Any
        if backend_env == "hnsw":
            from bijux_vex.infra.adapters.hnsw.backend import hnsw_backend

            backend = hnsw_backend(
                db_path=str(chosen_path),
                index_dir=os.getenv("BIJUX_VEX_HNSW_PATH"),
            )
        else:
            backend = sqlite_backend(str(chosen_path))
        _BACKEND_POOL[key] = backend
        return backend


def _resolve_correlation_id(raw: str | None) -> str:
    return raw or "req-1"


class Orchestrator:
    # This module is allowed to be “ugly but bounded”: wiring/glue only.
    # Domain rules belong in domain/core; do not reintroduce policy here.
    def __init__(
        self,
        backend: Any | None = None,
        authz: Authz | None = None,
        state_path: str | Path | None = None,
        config: ExecutionConfig | None = None,
    ) -> None:
        self.config = config or ExecutionConfig()
        if backend is not None:
            self.backend = backend
        else:
            backend_env = (os.getenv("BIJUX_VEX_BACKEND") or "").lower()
            chosen_raw: str | Path = (
                state_path or os.getenv("BIJUX_VEX_STATE_PATH") or "session.sqlite"
            )
            chosen_path = Path(chosen_raw)
            self.backend = _resolve_backend(backend_env, chosen_path)
        self.vector_store_enabled = self.config.vector_store is not None
        vector_store_cfg = self.config.vector_store or VectorStoreConfig(
            backend="memory"
        )
        self.vector_store_resolution = VECTOR_STORES.resolve(
            vector_store_cfg.backend or "memory",
            uri=vector_store_cfg.uri,
            options=vector_store_cfg.options,
        )
        log_event(
            "backend_selected",
            backend=getattr(self.backend, "name", "unknown"),
            vector_store=self.vector_store_resolution.descriptor.name,
        )
        self.stores = self.backend.stores
        if self.vector_store_enabled:
            self.stores = self.backend.stores._replace(
                vectors=VectorStoreVectorSource(
                    self.backend.stores.vectors, self.vector_store_resolution
                )
            )
        if authz is not None:
            self.authz = authz
        else:
            auth_mode = (os.getenv("BIJUX_VEX_AUTHZ_MODE") or "").lower()
            self.authz = (
                DenyAllAuthz() if auth_mode in {"deny", "deny_all"} else AllowAllAuthz()
            )
        ro = (os.getenv("BIJUX_VEX_READ_ONLY") or "").lower()
        self.read_only = ro in {"1", "true", "yes"}
        self.id_policy: IdGenerationStrategy = ContentAddressedIdPolicy()
        self.default_artifact_id = self.id_policy.next_artifact_id()
        self._latest_corpus_fingerprint: str | None = None
        self._latest_vector_fingerprint: str | None = None
        self._run_store = RunStore()
        self._idempotency_lock = threading.Lock()
        self._idempotency_cache: dict[str, dict[str, Any]] = {}
        self._nd_rate_limit = int(os.getenv("BIJUX_VEX_ND_RATE_LIMIT") or "0")
        self._nd_rate_window_seconds = int(
            os.getenv("BIJUX_VEX_ND_RATE_WINDOW_S") or "60"
        )
        self._nd_rate_window_start = time.time()
        self._nd_rate_count = 0
        self._nd_circuit_failures = 0
        self._nd_circuit_max_failures = int(
            os.getenv("BIJUX_VEX_ND_CIRCUIT_MAX_FAILURES") or "3"
        )
        self._nd_circuit_cooldown_s = int(
            os.getenv("BIJUX_VEX_ND_CIRCUIT_COOLDOWN_S") or "30"
        )
        self._nd_circuit_open_until = 0.0

    def _tx(self) -> Tx:
        return cast(Tx, self.backend.tx_factory())

    def _guard_mutation(self, action: str) -> None:
        if self.read_only:
            raise AuthzDeniedError(
                message=f"Mutation '{action}' disallowed in read-only mode"
            )

    def _require_artifact(self, artifact_id: str) -> ExecutionArtifact:
        artifact = self.stores.ledger.get_artifact(artifact_id)
        if artifact is None:
            raise NotFoundError(message=f"Execution artifact {artifact_id} not found")
        return cast(ExecutionArtifact, artifact)

    def _artifact_build_params(self) -> tuple[tuple[str, str], ...]:
        if not self.vector_store_enabled:
            return ()
        metadata = getattr(self.stores.vectors, "vector_store_metadata", None)
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

    @staticmethod
    def _metadata_tuple(
        meta: dict[str, str | None],
    ) -> tuple[tuple[str, str], ...] | None:
        items = tuple((k, v) for k, v in meta.items() if v is not None)
        return items or None

    def list_artifacts(
        self, *, limit: int | None = None, offset: int = 0
    ) -> dict[str, Any]:
        artifacts = [a.artifact_id for a in self.stores.ledger.list_artifacts()]
        if offset:
            artifacts = artifacts[offset:]
        if limit is not None:
            artifacts = artifacts[:limit]
        return {"artifacts": artifacts}

    def _validate_execute_limits(self, req: ExecutionRequestPayload) -> None:
        if req.vector is None:
            raise ValidationError(message="execution vector required")
        limits = self.config.resource_limits
        if limits and limits.max_k is not None and req.top_k > int(limits.max_k):
            raise BudgetExceededError(message="top_k exceeds max_k limit")
        if (
            limits
            and limits.max_query_size is not None
            and req.request_text
            and len(req.request_text) > int(limits.max_query_size)
        ):
            raise BudgetExceededError(
                message="request_text exceeds max_query_size limit"
            )

    def _resolve_execution_artifact(
        self, req: ExecutionRequestPayload
    ) -> ExecutionArtifact:
        artifact_id = req.artifact_id
        if artifact_id is None:
            available = tuple(self.stores.ledger.list_artifacts())
            if len(available) == 1:
                artifact_id = available[0].artifact_id
            else:
                raise ValidationError(message="artifact_id required for execution")
        artifact = self._require_artifact(artifact_id)
        if artifact.execution_contract is not req.execution_contract:
            raise InvariantError(
                message="Execution contract does not match artifact execution contract"
            )
        return artifact

    def _enforce_nd_circuit(self, req: ExecutionRequestPayload) -> None:
        if req.execution_contract is not ExecutionContract.NON_DETERMINISTIC:
            return
        now = time.time()
        if now < self._nd_circuit_open_until:
            raise BackendUnavailableError(
                message="ND backend temporarily unavailable (circuit open)"
            )
        if self._nd_rate_limit > 0:
            if now - self._nd_rate_window_start > self._nd_rate_window_seconds:
                self._nd_rate_window_start = now
                self._nd_rate_count = 0
            self._nd_rate_count += 1
            if self._nd_rate_count > self._nd_rate_limit:
                raise BudgetExceededError(
                    message="ND rate limit exceeded for this node"
                )

    def _build_randomness_profile(
        self, req: ExecutionRequestPayload
    ) -> RandomnessProfile | None:
        randomness_budget = None
        if req.execution_budget:
            randomness_budget = {
                key: value
                for key, value in {
                    "max_latency_ms": req.execution_budget.max_latency_ms,
                    "max_memory_mb": req.execution_budget.max_memory_mb,
                    "max_error": req.execution_budget.max_error,
                }.items()
                if value is not None
            }
        if not req.randomness_profile:
            return None
        return RandomnessProfile(
            seed=req.randomness_profile.seed,
            sources=tuple(req.randomness_profile.sources or ()),
            bounded=req.randomness_profile.bounded,
            non_replayable=req.randomness_profile.non_replayable,
            budget=randomness_budget if randomness_budget else None,
            envelopes=tuple(
                (k, float(v))
                for k, v in (randomness_budget or {}).items()
                if isinstance(v, (int, float))
            ),
        )

    def _build_execution_request(
        self,
        req: ExecutionRequestPayload,
        correlation_id: str,
        nd_settings: NDSettings | None,
    ) -> ExecutionRequest:
        return ExecutionRequest(
            request_id=correlation_id,
            text=req.request_text,
            vector=tuple(req.vector or ()),
            top_k=req.top_k,
            execution_contract=req.execution_contract,
            execution_intent=req.execution_intent,
            execution_mode=req.execution_mode,
            execution_budget=ExecutionBudget(
                max_latency_ms=req.execution_budget.max_latency_ms
                if req.execution_budget
                else None,
                max_memory_mb=req.execution_budget.max_memory_mb
                if req.execution_budget
                else None,
                max_error=req.execution_budget.max_error
                if req.execution_budget
                else None,
            ),
            nd_settings=nd_settings,
        )

    def _build_run_metadata(
        self,
        req: ExecutionRequestPayload,
        artifact: ExecutionArtifact,
        ann_index_info: dict[str, object] | None,
        vector_store_consistency: str | None,
        vector_store_index_params: object | None,
        backend_fingerprint: str,
        determinism_fp: str,
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
            "backend": getattr(self.backend, "name", "unknown"),
            "vector_store": {
                "backend": self.vector_store_resolution.descriptor.name,
                "uri_redacted": self.vector_store_resolution.uri_redacted,
                "supports_exact": self.vector_store_resolution.descriptor.supports_exact,
                "supports_ann": self.vector_store_resolution.descriptor.supports_ann,
                "consistency": vector_store_consistency,
            },
            "ann_index": ann_index_info,
            "determinism_fingerprints": {
                "vectors": artifact.vector_fingerprint,
                "config": artifact.index_config_fingerprint,
                "backend": backend_fingerprint,
                "determinism": determinism_fp,
            },
        }

    def capabilities(self) -> dict[str, Any]:
        caps = getattr(self.stores, "capabilities", None)
        supports_ann = False
        ann_runner = getattr(self.backend, "ann", None)
        default_runner = None
        nd_notes: list[str] = []
        if ann_runner is not None:
            default_runner = (
                "hnsw"
                if ann_runner.__class__.__name__ == "HnswAnnRunner"
                else "reference"
            )
            if default_runner == "reference":
                nd_notes.append("hnswlib not installed; using reference ANN runner")
        nd_health = {
            "status": "open" if time.time() < self._nd_circuit_open_until else "closed",
            "failures": self._nd_circuit_failures,
            "open_until": self._nd_circuit_open_until,
            "cooldown_s": self._nd_circuit_cooldown_s,
        }
        if caps is not None:
            supports_ann = bool(
                caps.supports_ann if caps.supports_ann is not None else caps.ann_support
            )
        ann_status = "experimental" if supports_ann else "unavailable"
        execution_modes = [mode.value for mode in ExecutionMode]
        storage_backends = [
            {
                "name": "memory",
                "status": "stable",
                "persistence": "ephemeral",
            },
            {
                "name": "sqlite",
                "status": "stable",
                "persistence": "local",
            },
            {
                "name": "hnsw",
                "status": "experimental",
                "persistence": "local",
            },
            {
                "name": "pgvector",
                "status": "experimental_excluded",
                "persistence": "external",
                "notes": "excluded from v1 freeze",
            },
        ]
        vector_stores = [
            {
                "name": desc.name,
                "available": desc.available,
                "supports_exact": desc.supports_exact,
                "supports_ann": desc.supports_ann,
                "delete_supported": desc.delete_supported,
                "filtering_supported": desc.filtering_supported,
                "deterministic_exact": desc.deterministic_exact,
                "experimental": desc.experimental,
                "consistency": desc.consistency,
                "version": desc.version,
                "notes": desc.notes,
            }
            for desc in VECTOR_STORES.descriptors()
        ]
        plugins = {
            "vectorstores": VECTOR_STORES.plugin_reports(),
            "embeddings": EMBEDDING_PROVIDERS.plugin_reports(),
            "runners": RUNNERS.plugin_reports(),
        }
        if caps is None:
            return {
                "backend": getattr(self.backend, "name", "unknown"),
                "contracts": [],
                "deterministic_query": None,
                "supports_ann": False,
                "replayable": None,
                "metrics": [],
                "max_vector_size": None,
                "isolation_level": None,
                "execution_modes": execution_modes,
                "ann_status": ann_status,
                "nd": {
                    "default_runner": default_runner,
                    "health": nd_health,
                    "notes": tuple(nd_notes),
                },
                "storage_backends": storage_backends,
                "vector_stores": vector_stores,
                "plugins": plugins,
            }
        return {
            "backend": getattr(self.backend, "name", "unknown"),
            "contracts": sorted(
                c.value if hasattr(c, "value") else str(c)
                for c in (caps.contracts or [])
            ),
            "deterministic_query": caps.deterministic_query,
            "supports_ann": supports_ann,
            "replayable": caps.replayable,
            "metrics": sorted(caps.metrics or []),
            "max_vector_size": caps.max_vector_size,
            "isolation_level": caps.isolation_level,
            "execution_modes": execution_modes,
            "ann_status": ann_status,
            "nd": {
                "default_runner": default_runner,
                "health": nd_health,
                "notes": tuple(nd_notes),
            },
            "storage_backends": storage_backends,
            "vector_stores": vector_stores,
            "plugins": plugins,
        }

    def create(self, req: CreateRequest) -> dict[str, Any]:
        self._guard_mutation("create")
        return {"name": req.name, "status": "created"}

    def ingest(self, req: IngestRequest) -> dict[str, Any]:
        self._guard_mutation("ingest")
        limits = self.config.resource_limits
        if (
            limits
            and limits.max_vectors_per_ingest is not None
            and len(req.documents) > int(limits.max_vectors_per_ingest)
        ):
            raise BudgetExceededError(
                message="ingest exceeds max_vectors_per_ingest limit"
            )
        if req.idempotency_key:
            with self._idempotency_lock:
                cached = self._idempotency_cache.get(req.idempotency_key)
                if cached is not None:
                    return dict(cached)
        correlation_id = _resolve_correlation_id(req.correlation_id)
        log_event(
            "ingest_start", correlation_id=correlation_id, count=len(req.documents)
        )
        vectors_input = list(req.vectors or [])
        vectors: list[list[float]] = []
        embedding_meta_by_index: dict[int, dict[str, str | None]] = {}
        embedding_model: str | None = None
        if vectors_input:
            vectors = vectors_input
        else:
            embed_provider = None
            embed_model = None
            cache_spec = None
            if self.config.embeddings is not None:
                embed_provider = self.config.embeddings.provider
                embed_model = self.config.embeddings.model
                if self.config.embeddings.cache is not None:
                    cache_spec = (
                        self.config.embeddings.cache.uri
                        or self.config.embeddings.cache.backend
                    )
            embed_provider = embed_provider or req.embed_provider
            embed_model = embed_model or req.embed_model
            cache_spec = cache_spec or req.cache_embeddings
            if not embed_model:
                raise ValidationError(
                    message="embed_model required when vectors are omitted"
                )
            embedding_model = embed_model
            try:
                provider = EMBEDDING_PROVIDERS.resolve(embed_provider)
            except ValueError as exc:
                raise ValidationError(message=str(exc)) from exc
            options: dict[str, str] = {"normalize": "false"}
            config_hash = embedding_config_hash(
                provider.name,
                embed_model,
                options,
                provider_version=provider.provider_version,
            )
            try:
                cache = build_cache(cache_spec)
            except ValueError as exc:
                raise ValidationError(message=str(exc)) from exc
            pending_texts: list[str] = []
            pending_idx: list[int] = []
            vectors = [[0.0] for _ in req.documents]
            if cache is not None:
                for idx, doc_text in enumerate(req.documents):
                    key = cache_key(embed_model, doc_text, config_hash)
                    entry = cache.get(key)
                    if entry:
                        expected = {
                            "embedding_provider": provider.name,
                            "embedding_provider_version": provider.provider_version,
                            "embedding_normalization": options.get("normalize"),
                        }
                        if any(
                            entry.metadata.get(k) != ("" if v is None else str(v))
                            for k, v in expected.items()
                        ):
                            entry = None
                    if entry:
                        vectors[idx] = list(entry.vector)
                        embedding_meta_by_index[idx] = entry.metadata
                    else:
                        pending_texts.append(doc_text)
                        pending_idx.append(idx)
            else:
                pending_texts = list(req.documents)
                pending_idx = list(range(len(req.documents)))
            if pending_texts:
                batch = provider.embed(pending_texts, embed_model, options=options)
                if len(batch.vectors) != len(pending_idx):
                    raise ValidationError(
                        message="embedding provider returned mismatched vector count"
                    )
                if not batch.metadata.embedding_determinism:
                    raise ValidationError(
                        message="embedding provider did not declare determinism"
                    )
                for idx, embed_vec in zip(pending_idx, batch.vectors, strict=False):
                    vectors[idx] = list(embed_vec)
                    meta_dict = metadata_as_dict(
                        {
                            "embedding_provider": batch.metadata.provider,
                            "embedding_provider_version": batch.metadata.provider_version,
                            "embedding_model_version": batch.metadata.model_version,
                            "embedding_determinism": batch.metadata.embedding_determinism,
                            "embedding_seed": batch.metadata.embedding_seed,
                            "embedding_device": batch.metadata.embedding_device,
                            "embedding_dtype": batch.metadata.embedding_dtype,
                            "embedding_normalization": batch.metadata.embedding_normalization,
                        }
                    )
                    embedding_meta_by_index[idx] = meta_dict
                    if cache is not None:
                        key = cache_key(
                            batch.metadata.model,
                            req.documents[idx],
                            batch.metadata.config_hash,
                        )
                        from bijux_vex.infra.embeddings.cache import EmbeddingCacheEntry

                        cache.set(
                            key,
                            entry=EmbeddingCacheEntry(
                                vector=tuple(embed_vec),
                                metadata=meta_dict,
                            ),
                        )
        with timed("ingest_latency_ms") as elapsed, self._tx() as tx:
            for idx, doc_text in enumerate(req.documents):
                doc_id = self.id_policy.document_id(doc_text)
                doc = Document(document_id=doc_id, text=doc_text)
                self.authz.check(tx, action="put_document", resource="document")
                self.stores.vectors.put_document(tx, doc)
                chunk = Chunk(
                    chunk_id=self.id_policy.chunk_id(doc.document_id, 0),
                    document_id=doc.document_id,
                    text=doc_text,
                    ordinal=0,
                )
                self.authz.check(tx, action="put_chunk", resource="chunk")
                self.stores.vectors.put_chunk(tx, chunk)
                vec = Vector(
                    vector_id=self.id_policy.vector_id(
                        chunk.chunk_id, tuple(vectors[idx])
                    ),
                    chunk_id=chunk.chunk_id,
                    values=tuple(vectors[idx]),
                    dimension=len(vectors[idx]),
                    model=embedding_model,
                    metadata=self._metadata_tuple(embedding_meta_by_index.get(idx, {}))
                    if embedding_meta_by_index
                    else None,
                )
                self.authz.check(tx, action="put_vector", resource="vector")
                self.stores.vectors.put_vector(tx, vec)
        METRICS.increment("vectors_indexed_total", value=len(req.documents))
        log_event("ingest_end", correlation_id=correlation_id, elapsed_ms=elapsed())
        self._latest_corpus_fingerprint = corpus_fingerprint(req.documents)
        self._latest_vector_fingerprint = vectors_fingerprint(vectors)
        existing_artifact = self.stores.ledger.get_artifact(self.default_artifact_id)
        if (
            existing_artifact
            and existing_artifact.execution_contract
            is ExecutionContract.NON_DETERMINISTIC
            and existing_artifact.index_state == "ready"
        ):
            updated = replace(existing_artifact, index_state="invalidated")
            with self._tx() as tx:
                self.stores.ledger.put_artifact(tx, updated)
            log_event(
                "ann_index_invalidated",
                artifact_id=existing_artifact.artifact_id,
            )
        result = {"ingested": len(req.documents), "correlation_id": correlation_id}
        if req.idempotency_key:
            with self._idempotency_lock:
                self._idempotency_cache[req.idempotency_key] = dict(result)
        return result

    def materialize(self, req: ExecutionArtifactRequest) -> dict[str, Any]:
        self._guard_mutation("materialize")
        index_mode = (req.index_mode or "exact").lower()
        if index_mode not in {"exact", "ann"}:
            raise ValidationError(message="index_mode must be exact|ann")
        existing = self.stores.ledger.get_artifact(self.default_artifact_id)
        if existing and existing.execution_contract is not req.execution_contract:
            raise InvariantError(
                message="Cannot rebuild artifact with different execution contract"
            )
        if (
            index_mode == "ann"
            and req.execution_contract is ExecutionContract.DETERMINISTIC
        ):
            raise ValidationError(
                message="ANN materialize requires non_deterministic execution_contract"
            )
        artifact = ExecutionArtifact(
            artifact_id=self.default_artifact_id,
            corpus_fingerprint=self._latest_corpus_fingerprint
            or corpus_fingerprint(()),
            vector_fingerprint=self._latest_vector_fingerprint
            or vectors_fingerprint(()),
            metric="l2",
            scoring_version="v1",
            schema_version="v1",
            execution_contract=req.execution_contract,
            build_params=self._artifact_build_params(),
            index_state="unbuilt"
            if req.execution_contract is ExecutionContract.NON_DETERMINISTIC
            else "ready",
        )
        plan = ExecutionPlan(
            algorithm="exact_vector_execution",
            contract=req.execution_contract,
            k=0,
            scoring_fn=artifact.metric,
            randomness_sources=(),
            reproducibility_bounds="bit-identical",
        )
        execution_id = derive_execution_id(
            request=ExecutionRequest(
                request_id="materialize",
                text=None,
                vector=None,
                top_k=0,
                execution_contract=req.execution_contract,
                execution_intent=ExecutionIntent.EXACT_VALIDATION,
                execution_mode=(
                    ExecutionMode.STRICT
                    if req.execution_contract is ExecutionContract.DETERMINISTIC
                    else ExecutionMode.BOUNDED
                ),
                execution_budget=(
                    ExecutionBudget()
                    if req.execution_contract is ExecutionContract.NON_DETERMINISTIC
                    else None
                ),
            ),
            backend_id=getattr(self.backend, "name", "unknown"),
            algorithm="exact_vector_execution",
            plan=plan,
        )
        artifact = replace(
            artifact,
            execution_plan=plan,
            execution_signature=execution_signature(
                plan, artifact.corpus_fingerprint, artifact.vector_fingerprint, None
            ),
            execution_id=execution_id,
        )
        if index_mode == "ann":
            ann_runner = getattr(self.backend, "ann", None)
            if ann_runner is None:
                raise NDExecutionUnavailableError(
                    message="ANN runner required to build ANN index"
                )
            vectors = list(self.stores.vectors.list_vectors())
            index_info = ann_runner.build_index(
                artifact.artifact_id, vectors, artifact.metric, None
            )
            if index_info:
                index_hash = index_info.get("index_hash")
                extra: tuple[tuple[str, str], ...] = (
                    ("ann_index_info", json.dumps(index_info, sort_keys=True)),
                )
                if index_hash:
                    extra = extra + (("ann_index_hash", str(index_hash)),)
                artifact = replace(
                    artifact,
                    build_params=artifact.build_params + extra,
                    index_state="ready",
                )
        with self._tx() as tx:
            self.authz.check(tx, action="put_artifact", resource="artifact")
            self.stores.ledger.put_artifact(tx, artifact)
        log_event("artifact_write", artifact_id=artifact.artifact_id)
        return {
            "artifact_id": artifact.artifact_id,
            "execution_contract": artifact.execution_contract.value,
            "execution_contract_status": (
                "stable"
                if artifact.execution_contract is ExecutionContract.DETERMINISTIC
                else "experimental"
            ),
            "replayable": artifact.replayable,
        }

    def execute(self, req: ExecutionRequestPayload) -> dict[str, Any]:
        (
            correlation_id,
            run_id,
            artifact,
            randomness_profile,
            nd_model,
            request,
        ) = self._normalize_execute_request(req)
        vector_store_meta = getattr(self.stores.vectors, "vector_store_metadata", None)
        vector_store_index_params = None
        vector_store_consistency = None
        if isinstance(vector_store_meta, dict):
            vector_store_index_params = vector_store_meta.get("index_params")
            vector_store_consistency = vector_store_meta.get("consistency")
        ann_index_info: dict[str, object] | None = None
        ann_runner = getattr(self.backend, "ann", None)
        if (
            artifact.execution_contract is ExecutionContract.NON_DETERMINISTIC
            and ann_runner is not None
            and hasattr(ann_runner, "index_info")
        ):
            ann_index_info = ann_runner.index_info(artifact.artifact_id)
        backend_fingerprint = fingerprint(
            {
                "backend": getattr(self.backend, "name", "unknown"),
                "vector_store": {
                    "backend": self.vector_store_resolution.descriptor.name,
                    "version": self.vector_store_resolution.descriptor.version,
                    "consistency": vector_store_consistency,
                    "index_params": vector_store_index_params,
                },
            }
        )
        determinism_fp = determinism_fingerprint(
            artifact.vector_fingerprint,
            artifact.index_config_fingerprint,
            artifact.execution_plan.algorithm if artifact.execution_plan else None,
        )
        run_metadata = self._build_run_metadata(
            req,
            artifact,
            ann_index_info,
            vector_store_consistency,
            vector_store_index_params,
            backend_fingerprint,
            determinism_fp,
            correlation_id,
        )
        self._run_store.start(run_id, run_metadata)
        log_event("query_start", correlation_id=correlation_id, top_k=req.top_k)
        try:
            with timed("query_latency_ms") as elapsed:
                execution_result, results = self._dispatch_execution(
                    req,
                    artifact,
                    request,
                    randomness_profile,
                    nd_model,
                )
            log_event("query_end", correlation_id=correlation_id, elapsed_ms=elapsed())
            limits = self.config.resource_limits
            if (
                limits
                and limits.max_execution_time_ms is not None
                and elapsed() > float(limits.max_execution_time_ms)
            ):
                raise BudgetExceededError(
                    message="Execution exceeded max_execution_time_ms limit"
                )
            if req.execution_contract is ExecutionContract.NON_DETERMINISTIC:
                self._nd_circuit_failures = 0
            return self._finalize_execution(
                artifact,
                execution_result,
                results,
                run_id,
                correlation_id,
            )
        except Exception as exc:
            if req.execution_contract is ExecutionContract.NON_DETERMINISTIC:
                self._nd_circuit_failures += 1
                if self._nd_circuit_failures >= self._nd_circuit_max_failures:
                    self._nd_circuit_open_until = (
                        time.time() + self._nd_circuit_cooldown_s
                    )
                    log_event(
                        "nd_circuit_open",
                        failures=self._nd_circuit_failures,
                        cooldown_s=self._nd_circuit_cooldown_s,
                    )
            details = refusal_payload(exc) if is_refusal(exc) else None
            self._run_store.mark_failed(run_id, str(exc), details=details)
            raise

    def _normalize_execute_request(
        self, req: ExecutionRequestPayload
    ) -> tuple[
        str,
        str,
        ExecutionArtifact,
        RandomnessProfile | None,
        NDExecutionModel,
        ExecutionRequest,
    ]:
        self._validate_execute_limits(req)
        correlation_id = _resolve_correlation_id(req.correlation_id)
        run_id = f"{correlation_id}-{uuid.uuid4().hex}"
        artifact = self._resolve_execution_artifact(req)
        randomness_profile = self._build_randomness_profile(req)
        nd_model = NDExecutionModel(
            stores=self.stores,
            ann_runner=getattr(self.backend, "ann", None),
            latest_vector_fingerprint=self._latest_vector_fingerprint,
            tx_factory=self._tx,
        )
        nd_settings = nd_model.build_settings(req)
        request = self._build_execution_request(req, correlation_id, nd_settings)
        if req.execution_contract is ExecutionContract.NON_DETERMINISTIC:
            self._enforce_nd_circuit(req)
        return (
            correlation_id,
            run_id,
            artifact,
            randomness_profile,
            nd_model,
            request,
        )

    def _dispatch_execution(
        self,
        req: ExecutionRequestPayload,
        artifact: ExecutionArtifact,
        request: ExecutionRequest,
        randomness_profile: RandomnessProfile | None,
        nd_model: NDExecutionModel,
    ) -> tuple[Any, Any]:
        if req.execution_contract is ExecutionContract.NON_DETERMINISTIC:
            return nd_model.execute(
                artifact,
                request,
                randomness_profile,
                build_on_demand=req.nd_build_on_demand,
            )
        session = start_execution_session(
            artifact,
            request,
            self.stores,
            randomness=randomness_profile,
            ann_runner=getattr(self.backend, "ann", None),
        )
        return execute_request(
            session,
            self.stores,
            ann_runner=getattr(self.backend, "ann", None),
        )

    def _finalize_execution(
        self,
        artifact: ExecutionArtifact,
        execution_result: Any,
        results: Any,
        run_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        with self._tx() as tx:
            self.stores.ledger.put_execution_result(tx, execution_result)
            updated_artifact = replace(
                artifact,
                execution_plan=execution_result.plan,
                execution_signature=execution_result.signature,
                execution_id=execution_result.execution_id,
            )
            self.stores.ledger.put_artifact(tx, updated_artifact)
            artifact = updated_artifact
        nd_trace = None
        if execution_result.nd_result is not None:
            trace = execution_result.nd_result.decision_trace
            if trace is not None:
                from dataclasses import asdict

                nd_trace = asdict(trace)
        self._run_store.finalize(
            run_id,
            {
                "execution_result": execution_result.to_primitive(),
                "results": [r.vector_id for r in results],
                "nd_decision_trace": nd_trace,
            },
        )
        return {
            "results": [r.vector_id for r in results],
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

    def explain(self, req: ExplainRequest) -> dict[str, Any]:
        art_id = req.artifact_id
        if art_id is None:
            artifacts = tuple(self.stores.ledger.list_artifacts())
            if len(artifacts) == 1:
                art_id = artifacts[0].artifact_id
            else:
                raise ValidationError(message="artifact_id required to explain result")
        artifact = self._require_artifact(art_id)
        latest = self.stores.ledger.latest_execution_result(artifact.artifact_id)
        if latest is None:
            raise NotFoundError(message="No execution results available to explain")
        target = next((r for r in latest.results if r.vector_id == req.result_id), None)
        if target is None:
            raise NotFoundError(message="result not found")
        data = explain_result(target, self.stores)
        document = cast(Document, data["document"])
        chunk = cast(Chunk, data["chunk"])
        vector = cast(Vector, data["vector"])
        artifact_meta = cast(ExecutionArtifact, data["artifact"])
        return {
            "document_id": document.document_id,
            "chunk_id": chunk.chunk_id,
            "vector_id": vector.vector_id,
            "artifact_id": artifact_meta.artifact_id,
            "metric": artifact_meta.metric,
            "score": target.score,
            "correlation_id": target.request_id,
            "execution_contract": artifact_meta.execution_contract.value,
            "execution_contract_status": (
                "stable"
                if artifact_meta.execution_contract is ExecutionContract.DETERMINISTIC
                else "experimental"
            ),
            "replayable": artifact_meta.replayable,
            "execution_id": latest.execution_id,
        }

    def replay(
        self,
        request_text: str,
        expected_contract: ExecutionContract | None = None,
        artifact_id: str | None = None,
        randomness_profile: RandomnessProfile | None = None,
        execution_budget: ExecutionBudget | None = None,
    ) -> dict[str, Any]:
        chosen_artifact_id = artifact_id
        if chosen_artifact_id is None:
            artifacts = tuple(self.stores.ledger.list_artifacts())
            if len(artifacts) == 1:
                chosen_artifact_id = artifacts[0].artifact_id
            else:
                raise ValidationError(message="artifact_id required for replay")
        artifact = self._require_artifact(chosen_artifact_id)
        if expected_contract and expected_contract is not artifact.execution_contract:
            raise InvariantError(
                message="Replay contract does not match artifact execution contract"
            )
        if (
            artifact.execution_contract is ExecutionContract.NON_DETERMINISTIC
            and randomness_profile is None
        ):
            raise ReplayNotSupportedError(
                message="Non-deterministic replay requires explicit randomness profile"
            )
        if (
            artifact.execution_contract is ExecutionContract.NON_DETERMINISTIC
            and randomness_profile is not None
            and randomness_profile.non_replayable
        ):
            raise ReplayNotSupportedError(
                message="Non-deterministic replay refused for non-replayable requests"
            )
        if (
            artifact.execution_contract is ExecutionContract.NON_DETERMINISTIC
            and randomness_profile is not None
            and randomness_profile.seed is None
        ):
            raise ReplayNotSupportedError(
                message="Non-deterministic replay requires a seed"
            )
        request = ExecutionRequest(
            request_id="req-replay",
            text=request_text,
            vector=(0.0, 0.0),
            top_k=5,
            execution_contract=artifact.execution_contract,
            execution_intent=ExecutionIntent.REPRODUCIBLE_RESEARCH,
            execution_mode=ExecutionMode.STRICT
            if artifact.execution_contract is ExecutionContract.DETERMINISTIC
            else ExecutionMode.BOUNDED,
            execution_budget=execution_budget,
        )
        outcome = replay(
            request,
            artifact,
            self.stores,
            ann_runner=getattr(self.backend, "ann", None),
            randomness=randomness_profile,
        )
        return {
            "matches": outcome.matches,
            "original_fingerprint": outcome.original_fingerprint,
            "replay_fingerprint": outcome.replay_fingerprint,
            "details": outcome.details,
            "nondeterministic_sources": outcome.nondeterministic_sources,
            "execution_contract": artifact.execution_contract.value,
            "execution_contract_status": (
                "stable"
                if artifact.execution_contract is ExecutionContract.DETERMINISTIC
                else "experimental"
            ),
            "replayable": artifact.replayable,
            "execution_id": outcome.execution_id,
        }

    def compare(
        self,
        req: ExecutionRequestPayload,
        artifact_a_id: str | None = None,
        artifact_b_id: str | None = None,
    ) -> dict[str, object]:
        if req.vector is None:
            raise ValidationError(message="execution vector required for comparison")
        art_a = self._require_artifact(artifact_a_id or self.default_artifact_id)
        art_b = self._require_artifact(artifact_b_id or self.default_artifact_id)
        vector_values = tuple(req.vector)

        def _as_request(artifact: ExecutionArtifact) -> ExecutionRequest:
            return ExecutionRequest(
                request_id=f"compare-{artifact.artifact_id}",
                text=req.request_text,
                vector=vector_values,
                top_k=req.top_k,
                execution_contract=artifact.execution_contract,
                execution_intent=req.execution_intent,
                execution_mode=req.execution_mode,
                execution_budget=ExecutionBudget(
                    max_latency_ms=req.execution_budget.max_latency_ms
                    if req.execution_budget
                    else None,
                    max_memory_mb=req.execution_budget.max_memory_mb
                    if req.execution_budget
                    else None,
                    max_error=req.execution_budget.max_error
                    if req.execution_budget
                    else None,
                ),
            )

        req_a = _as_request(art_a)
        req_b = _as_request(art_b)
        ann_runner = getattr(self.backend, "ann", None)
        session_a = start_execution_session(
            art_a, req_a, self.stores, ann_runner=ann_runner
        )
        session_b = start_execution_session(
            art_b, req_b, self.stores, ann_runner=ann_runner
        )
        exec_a, res_a = execute_request(session_a, self.stores, ann_runner=ann_runner)
        exec_b, res_b = execute_request(session_b, self.stores, ann_runner=ann_runner)
        diff = compare_executions(exec_a, res_a, exec_b, res_b)
        return {
            "execution_a": diff.execution_a.execution_id,
            "execution_b": diff.execution_b.execution_id,
            "overlap_ratio": diff.overlap_ratio,
            "recall_delta": diff.recall_delta,
            "rank_instability": diff.rank_instability,
            "execution_a_contract": art_a.execution_contract.value,
            "execution_b_contract": art_b.execution_contract.value,
            "execution_a_contract_status": (
                "stable"
                if art_a.execution_contract is ExecutionContract.DETERMINISTIC
                else "experimental"
            ),
            "execution_b_contract_status": (
                "stable"
                if art_b.execution_contract is ExecutionContract.DETERMINISTIC
                else "experimental"
            ),
        }
