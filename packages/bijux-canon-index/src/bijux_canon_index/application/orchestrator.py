# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from bijux_canon_index.application.orchestration.capabilities_report import (
    build_capabilities_response,
)
from bijux_canon_index.application.orchestration.execution_tracking import (
    build_execution_tracking_context,
)
from bijux_canon_index.application.orchestration.idempotency_cache import (
    IdempotencyCache,
)
from bijux_canon_index.application.orchestration.nd_guard import NDExecutionGuard
from bijux_canon_index.application.orchestration.execution_runtime import (
    build_execution_request,
    build_randomness_profile,
    dispatch_execution,
    normalize_execute_request,
    resolve_correlation_id,
    resolve_execution_artifact,
    validate_execute_limits,
)
from bijux_canon_index.application.orchestration.ingest_embeddings import (
    prepare_ingest_vectors,
)
from bijux_canon_index.application.orchestration.ingest_persistence import (
    invalidate_ann_artifact_if_needed,
    persist_ingest_documents,
)
from bijux_canon_index.application.orchestration.materialization import (
    attach_ann_index,
    build_materialized_artifact,
    materialization_response,
)
from bijux_canon_index.application.orchestration.query_introspection import (
    build_compare_response,
    build_explain_response,
    build_replay_response,
)
from bijux_canon_index.application.orchestration.result_records import (
    artifact_build_params,
    build_run_metadata,
    finalize_execution,
    metadata_tuple,
)
from bijux_canon_index.application.orchestration.runtime_bootstrap import (
    bootstrap_runtime,
)
from bijux_canon_index.contracts.authz import Authz
from bijux_canon_index.contracts.tx import Tx
from bijux_canon_index.core.config import ExecutionConfig
from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.errors import (
    AuthzDeniedError,
    BudgetExceededError,
    InvariantError,
    NDExecutionUnavailableError,
    NotFoundError,
    ValidationError,
)
from bijux_canon_index.core.errors.refusal import is_refusal, refusal_payload
from bijux_canon_index.core.identity.fingerprints import (
    corpus_fingerprint,
    vectors_fingerprint,
)
from bijux_canon_index.core.runtime.vector_execution import RandomnessProfile
from bijux_canon_index.core.types import (
    ExecutionArtifact,
    ExecutionBudget,
    ExecutionRequest,
    NDSettings,
)
from bijux_canon_index.domain.non_determinism.execution_model import (
    NonDeterministicExecutionModel,
)
from bijux_canon_index.infra.logging import log_event
from bijux_canon_index.infra.metrics import METRICS, timed
from bijux_canon_index.infra.run_store import RunStore
from bijux_canon_index.interfaces.schemas.requests import (
    CreateRequest,
    ExecutionArtifactRequest,
    ExecutionRequestPayload,
    ExplainRequest,
    IngestRequest,
)


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
        runtime = bootstrap_runtime(
            backend=backend,
            authz=authz,
            state_path=state_path,
            config=self.config,
        )
        self.backend = runtime.backend
        self.vector_store_enabled = runtime.vector_store_enabled
        self.vector_store_resolution = runtime.vector_store_resolution
        self.stores = runtime.stores
        self.authz = runtime.authz
        self.read_only = runtime.read_only
        self.id_policy = runtime.id_policy
        self.default_artifact_id = runtime.default_artifact_id
        self._latest_corpus_fingerprint: str | None = None
        self._latest_vector_fingerprint: str | None = None
        self._run_store = RunStore()
        self._idempotency_cache = IdempotencyCache()
        self._nd_guard = NDExecutionGuard(
            rate_limit=runtime.nd_rate_limit,
            rate_window_seconds=runtime.nd_rate_window_seconds,
            max_failures=runtime.nd_circuit_max_failures,
            cooldown_seconds=runtime.nd_circuit_cooldown_s,
        )

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
        return artifact_build_params(
            vector_store_enabled=self.vector_store_enabled,
            stores=self.stores,
        )

    @staticmethod
    def _metadata_tuple(
        meta: dict[str, str | None],
    ) -> tuple[tuple[str, str], ...] | None:
        return metadata_tuple(meta)

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
        validate_execute_limits(self.config, req)

    def _resolve_execution_artifact(
        self, req: ExecutionRequestPayload
    ) -> ExecutionArtifact:
        return resolve_execution_artifact(
            req,
            default_artifact_id=self.default_artifact_id,
            stores=self.stores,
            require_artifact=self._require_artifact,
        )

    def _enforce_nd_circuit(self, req: ExecutionRequestPayload) -> None:
        if req.execution_contract is not ExecutionContract.NON_DETERMINISTIC:
            return
        self._nd_guard.enforce()

    def _build_randomness_profile(
        self, req: ExecutionRequestPayload
    ) -> RandomnessProfile | None:
        return build_randomness_profile(req)

    def _build_execution_request(
        self,
        req: ExecutionRequestPayload,
        correlation_id: str,
        nd_settings: NDSettings | None,
    ) -> ExecutionRequest:
        return build_execution_request(req, correlation_id, nd_settings)

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
        return build_run_metadata(
            req,
            artifact=artifact,
            ann_index_info=ann_index_info,
            vector_store_resolution=self.vector_store_resolution,
            vector_store_consistency=vector_store_consistency,
            backend_name=getattr(self.backend, "name", "unknown"),
            backend_fingerprint=backend_fingerprint,
            determinism_fingerprint=determinism_fp,
            correlation_id=correlation_id,
        )

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
        if caps is not None:
            supports_ann = bool(
                caps.supports_ann if caps.supports_ann is not None else caps.ann_support
            )
        return build_capabilities_response(
            backend_name=getattr(self.backend, "name", "unknown"),
            caps=caps,
            supports_ann=supports_ann,
            default_runner=default_runner,
            nd_health=self._nd_guard.health_report(),
            nd_notes=tuple(nd_notes),
        )

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
        cached = self._idempotency_cache.load(req.idempotency_key)
        if cached is not None:
            return cached
        correlation_id = resolve_correlation_id(req.correlation_id)
        log_event(
            "ingest_start", correlation_id=correlation_id, count=len(req.documents)
        )
        prepared_vectors = prepare_ingest_vectors(req, self.config)
        vectors = prepared_vectors.vectors
        embedding_meta_by_index = prepared_vectors.embedding_meta_by_index
        embedding_model = prepared_vectors.embedding_model
        with timed("ingest_latency_ms") as elapsed:
            persist_ingest_documents(
                tx_factory=self._tx,
                stores=self.stores,
                authz=self.authz,
                id_policy=self.id_policy,
                documents=req.documents,
                vectors=vectors,
                embedding_model=embedding_model,
                embedding_meta_by_index=embedding_meta_by_index,
                metadata_tuple=self._metadata_tuple,
            )
        METRICS.increment("vectors_indexed_total", value=len(req.documents))
        log_event("ingest_end", correlation_id=correlation_id, elapsed_ms=elapsed())
        self._latest_corpus_fingerprint = corpus_fingerprint(req.documents)
        self._latest_vector_fingerprint = vectors_fingerprint(vectors)
        invalidate_ann_artifact_if_needed(
            tx_factory=self._tx,
            stores=self.stores,
            artifact_id=self.default_artifact_id,
        )
        result = {"ingested": len(req.documents), "correlation_id": correlation_id}
        self._idempotency_cache.store(req.idempotency_key, result)
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
        artifact = build_materialized_artifact(
            artifact_id=self.default_artifact_id,
            request=req,
            corpus_fingerprint=self._latest_corpus_fingerprint
            or corpus_fingerprint(()),
            vector_fingerprint=self._latest_vector_fingerprint
            or vectors_fingerprint(()),
            build_params=self._artifact_build_params(),
            backend_name=getattr(self.backend, "name", "unknown"),
        )
        if index_mode == "ann":
            ann_runner = getattr(self.backend, "ann", None)
            if ann_runner is None:
                raise NDExecutionUnavailableError(
                    message="ANN runner required to build ANN index"
                )
            artifact = attach_ann_index(
                artifact=artifact,
                ann_runner=ann_runner,
                vectors=list(self.stores.vectors.list_vectors()),
            )
        with self._tx() as tx:
            self.authz.check(tx, action="put_artifact", resource="artifact")
            self.stores.ledger.put_artifact(tx, artifact)
        log_event("artifact_write", artifact_id=artifact.artifact_id)
        return materialization_response(artifact)

    def execute(self, req: ExecutionRequestPayload) -> dict[str, Any]:
        (
            correlation_id,
            run_id,
            artifact,
            randomness_profile,
            nd_model,
            request,
        ) = self._normalize_execute_request(req)
        tracking = build_execution_tracking_context(
            artifact=artifact,
            backend=self.backend,
            stores=self.stores,
            vector_store_resolution=self.vector_store_resolution,
        )
        run_metadata = self._build_run_metadata(
            req,
            artifact,
            tracking.ann_index_info,
            tracking.vector_store_consistency,
            tracking.vector_store_index_params,
            tracking.backend_fingerprint,
            tracking.determinism_fingerprint,
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
                self._nd_guard.record_success()
            return self._finalize_execution(
                artifact,
                execution_result,
                results,
                run_id,
                correlation_id,
            )
        except Exception as exc:
            if req.execution_contract is ExecutionContract.NON_DETERMINISTIC:
                self._nd_guard.record_failure()
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
        NonDeterministicExecutionModel,
        ExecutionRequest,
    ]:
        normalized = normalize_execute_request(
            req,
            config=self.config,
            stores=self.stores,
            default_artifact_id=self.default_artifact_id,
            require_artifact=self._require_artifact,
            latest_vector_fingerprint=self._latest_vector_fingerprint,
            tx_factory=self._tx,
            ann_runner=getattr(self.backend, "ann", None),
        )
        if req.execution_contract is ExecutionContract.NON_DETERMINISTIC:
            self._enforce_nd_circuit(req)
        return (
            normalized.correlation_id,
            normalized.run_id,
            normalized.artifact,
            normalized.randomness_profile,
            normalized.nd_model,
            normalized.request,
        )

    def _dispatch_execution(
        self,
        req: ExecutionRequestPayload,
        artifact: ExecutionArtifact,
        request: ExecutionRequest,
        randomness_profile: RandomnessProfile | None,
        nd_model: NonDeterministicExecutionModel,
    ) -> tuple[Any, Any]:
        return dispatch_execution(
            req,
            artifact=artifact,
            request=request,
            randomness_profile=randomness_profile,
            nd_model=nd_model,
            stores=self.stores,
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
        return finalize_execution(
            tx_factory=self._tx,
            stores=self.stores,
            run_store=self._run_store,
            artifact=artifact,
            execution_result=execution_result,
            results=results,
            run_id=run_id,
            correlation_id=correlation_id,
        )

    def explain(self, req: ExplainRequest) -> dict[str, Any]:
        return build_explain_response(
            req,
            stores=self.stores,
            require_artifact=self._require_artifact,
        )

    def replay(
        self,
        request_text: str,
        expected_contract: ExecutionContract | None = None,
        artifact_id: str | None = None,
        randomness_profile: RandomnessProfile | None = None,
        execution_budget: ExecutionBudget | None = None,
    ) -> dict[str, Any]:
        return build_replay_response(
            request_text,
            expected_contract=expected_contract,
            artifact_id=artifact_id,
            randomness_profile=randomness_profile,
            execution_budget=execution_budget,
            stores=self.stores,
            ann_runner=getattr(self.backend, "ann", None),
            require_artifact=self._require_artifact,
        )

    def compare(
        self,
        req: ExecutionRequestPayload,
        artifact_a_id: str | None = None,
        artifact_b_id: str | None = None,
    ) -> dict[str, object]:
        return build_compare_response(
            req,
            artifact_a_id=artifact_a_id,
            artifact_b_id=artifact_b_id,
            default_artifact_id=self.default_artifact_id,
            stores=self.stores,
            ann_runner=getattr(self.backend, "ann", None),
            require_artifact=self._require_artifact,
        )
