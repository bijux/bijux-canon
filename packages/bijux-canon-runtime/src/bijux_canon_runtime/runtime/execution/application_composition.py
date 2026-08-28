# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Production composition root for the shared Runtime v2 application service."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict
import gc
import hashlib
import json
from pathlib import Path
import tempfile
import threading
from time import perf_counter

from bijux_canon_index.application import (
    IndexGenerationArchive,
    IndexService,
    resolve_hybrid_retrieval_policy,
)
from bijux_canon_index.evaluation import PublicRetrievalEvaluator
from bijux_canon_index.infra.adapters.sqlite.lexical import SQLiteLexicalIndex
from bijux_canon_index.infra.embeddings.local_model import (
    EmbeddedBatch,
    LocalEmbeddingModel,
)
from bijux_canon_index.infra.embeddings.model_cache import load_model_lock
from bijux_canon_runtime.application.operations import (
    ApplicationCapabilityError,
    ReplayOperationRequest,
    RuntimeApplicationServicesV2,
    build_runtime_job_handlers,
)
from bijux_canon_runtime.application.profile_preflight import InstalledProfilePreflight
from bijux_canon_runtime.application.runtime_configuration import RuntimeConfiguration
from bijux_canon_runtime.application.workspace_initialization import (
    validate_runtime_workspace,
)
from bijux_canon_runtime.core.errors import ConfigurationError
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.execution.application_executor import (
    RuntimeExecutionService,
)
from bijux_canon_runtime.runtime.execution.durable_jobs import DurableJobManager
from bijux_canon_runtime.runtime.execution.installed_agent_adapter import (
    CanonicalAgentOperationAdapter,
)
from bijux_canon_runtime.runtime.execution.installed_operation_adapters import (
    CanonicalDenseIndexOperationAdapter,
    CanonicalEmbeddingOperationAdapter,
    CanonicalIngestOperationAdapter,
    CanonicalLexicalIndexOperationAdapter,
    CanonicalSnapshotOperationAdapter,
)
from bijux_canon_runtime.runtime.execution.installed_persistence_adapters import (
    CanonicalPersistenceOperationAdapter,
    CanonicalPublicationOperationAdapter,
)
from bijux_canon_runtime.runtime.execution.installed_reason_adapter import (
    CanonicalReasonOperationAdapter,
)
from bijux_canon_runtime.runtime.execution.installed_retrieval_adapter import (
    CanonicalRetrievalOperationAdapter,
)
from bijux_canon_runtime.runtime.execution.installed_verification_adapter import (
    CanonicalVerificationOperationAdapter,
)
from bijux_canon_runtime.runtime.execution.operation_dispatcher import (
    OperationDispatcher,
)
from bijux_canon_runtime.runtime.execution.retrieval_evaluation import (
    InstalledRetrievalEvaluationExecutor,
)
from bijux_canon_runtime.runtime.inspection import RuntimeRunInspector
from bijux_canon_runtime.runtime.persistence.authoritative_payload_store import (
    AuthoritativeArtifactPayloadStore,
)
from bijux_canon_runtime.runtime.persistence.filesystem_payload_store import (
    AtomicFilesystemArtifactPayloadStore,
)
from bijux_canon_runtime.runtime.replay.models import ReplayNetworkPolicy
from bijux_canon_runtime.runtime.replay.service import RuntimeReplayService


class _LazyLocalEmbeddingModel:
    """Load the verified local model only when an embedding step executes."""

    def __init__(self, model_root: Path) -> None:
        self._model_root = model_root
        self._model: LocalEmbeddingModel | None = None
        self._lock = threading.RLock()
        self._lock_content_sha256: str | None = None
        self._load_count = 0
        self._hit_count = 0
        self._invalidation_count = 0
        self._last_load_ms: float | None = None
        self._last_access_status = "cold"

    @property
    def model_lock_id(self) -> str:
        with self._lock:
            return self._load().model_lock_id

    def embed(self, texts: Sequence[str]) -> EmbeddedBatch:
        with self._lock:
            return self._load().embed(texts)

    def validate(self) -> str:
        """Prove actual locked dimension and numeric behavior before queueing."""
        with self._lock:
            result = self._load().embed(("bijux-canon offline model validation",))
            return result.model_lock_id

    def _load(self) -> LocalEmbeddingModel:
        with self._lock:
            lock_path = self._model_root / "model.lock.json"
            lock_content_sha256 = hashlib.sha256(lock_path.read_bytes()).hexdigest()
            if (
                self._model is not None
                and self._lock_content_sha256 == lock_content_sha256
            ):
                self._hit_count += 1
                self._last_access_status = "warm"
                return self._model
            started = perf_counter()
            lock = load_model_lock(lock_path)
            if (
                hashlib.sha256(lock_path.read_bytes()).hexdigest()
                != lock_content_sha256
            ):
                raise RuntimeError("embedding model lock changed while loading")
            replacement = LocalEmbeddingModel(self._model_root, lock)
            invalidated = self._model is not None
            if invalidated:
                self._invalidation_count += 1
            self._model = replacement
            self._lock_content_sha256 = lock_content_sha256
            self._load_count += 1
            self._last_load_ms = (perf_counter() - started) * 1000.0
            self._last_access_status = "invalidated" if invalidated else "cold"
            return self._model

    def cache_observation(self) -> dict[str, object]:
        """Return content-safe model reuse evidence without forcing a load."""
        with self._lock:
            return {
                "cache_identity": (
                    None if self._model is None else self._model.model_lock_id
                ),
                "hit_count": self._hit_count,
                "invalidation_count": self._invalidation_count,
                "last_load_ms": self._last_load_ms,
                "load_count": self._load_count,
                "schema_version": "bijux.canon.index.model_resource_cache.v1",
                "status": ("cold" if self._model is None else self._last_access_status),
            }

    def close(self) -> None:
        """Release the model reference when the application lifecycle ends."""
        with self._lock:
            self._model = None
            self._lock_content_sha256 = None
            self._last_access_status = "cold"
        gc.collect()


def compose_runtime_application_services(
    *,
    configuration: RuntimeConfiguration,
    max_workers: int = 4,
) -> RuntimeApplicationServicesV2:
    """Bind installed owners, durable jobs, CAS, inspection, and replay."""
    if max_workers < 1:
        raise ValueError("Runtime application worker count must be positive")
    try:
        validation = validate_runtime_workspace(configuration, verify_model=False)
        layout = configuration.require_workspace_layout()
    except ConfigurationError as exc:
        raise ApplicationCapabilityError(str(exc)) from exc
    filesystem_store = AtomicFilesystemArtifactPayloadStore(layout.cas_root)
    store = AuthoritativeArtifactPayloadStore(
        payload_store=filesystem_store,
        database_path=layout.database_path,
    )
    store.reconcile_inventory()
    index = IndexService(layout.index_root)
    embedding = _LazyLocalEmbeddingModel(layout.model_root)
    try:
        retrieval_policy = resolve_hybrid_retrieval_policy(
            configuration.retrieval_policy_id
        )
    except ValueError as exc:
        raise ApplicationCapabilityError(str(exc)) from exc
    dispatcher = OperationDispatcher(
        (
            CanonicalIngestOperationAdapter(),
            CanonicalSnapshotOperationAdapter(),
            CanonicalEmbeddingOperationAdapter(store=store, embedding=embedding),
            CanonicalLexicalIndexOperationAdapter(
                store=store,
                working_root=layout.operations_root,
            ),
            CanonicalDenseIndexOperationAdapter(
                index=index,
                working_root=layout.operations_root,
            ),
            CanonicalRetrievalOperationAdapter(
                store=store,
                index=index,
                embedding=embedding,
                vex_store_root=layout.vex_root,
                policy=retrieval_policy,
            ),
            CanonicalReasonOperationAdapter(semantic_encoder=embedding),
            CanonicalAgentOperationAdapter(
                store=store,
                index=index,
                embedding=embedding,
                vex_store_root=layout.vex_root,
                retrieval_policy=retrieval_policy,
            ),
            CanonicalVerificationOperationAdapter(),
            CanonicalPersistenceOperationAdapter(store=store),
            CanonicalPublicationOperationAdapter(),
        )
    )
    execution = RuntimeExecutionService(
        store=store,
        dispatcher=dispatcher,
        process_id=f"bijux-canon-runtime-v2:{validation.workspace_id}",
        configuration_identity_sha256=configuration.identity_sha256,
        max_workers=max_workers,
    )
    replay = RuntimeReplayService(store)

    def execute_replay(
        request: ReplayOperationRequest,
        is_cancelled: Callable[[], bool],
    ) -> dict[str, object]:
        live_dispatcher = (
            dispatcher
            if request.policy.network_policy is ReplayNetworkPolicy.PERMITTED
            else None
        )
        outcome = replay.replay(
            run_id=request.run_id,
            source_attempt_id=request.source_attempt_id,
            request_id=request.request_id,
            process_id=request.process_id,
            policy=request.policy,
            parent_job_id=request.parent_job_id,
            dispatcher=live_dispatcher,
            is_cancelled=is_cancelled,
        )
        return {
            "accepted": outcome.comparison.accepted,
            "exact_artifact_identities": (outcome.comparison.exact_artifact_identities),
            "replay_attempt_id": outcome.replay.selected_attempt_id,
            "reused": outcome.reused,
            "run_id": outcome.replay.run_id,
            "schema_version": "bijux.runtime.replay-result.v2",
        }

    jobs = DurableJobManager(
        layout.database_path,
        handlers=build_runtime_job_handlers(
            execute=execution.execute,
            replay=execute_replay,
        ),
        payload_store=store,
        legacy_database_path=layout.job_store_path,
        max_workers=max_workers,
    )
    inspector = RuntimeRunInspector(store)
    installed_retrieval_evaluation = InstalledRetrievalEvaluationExecutor(
        execution=execution,
        store=store,
        index=index,
    )

    def inspect_corpus(artifact_id: ArtifactID) -> dict[str, object]:
        artifact = store.load(artifact_id)
        if artifact.descriptor.schema_id != "ingest.corpus-snapshot.v1":
            raise ValueError("artifact is not a corpus snapshot")
        value = json.loads(artifact.canonical_bytes)
        if (
            not isinstance(value, dict)
            or not isinstance(value.get("documents"), list)
            or not isinstance(value.get("rejections"), list)
        ):
            raise ValueError("corpus snapshot payload is invalid")
        documents = value["documents"]
        assert isinstance(documents, list)
        rejections = value["rejections"]
        assert isinstance(rejections, list)
        parser_identities: set[tuple[str, str, str]] = set()
        chunk_count = 0
        for item in documents:
            if not isinstance(item, dict):
                raise ValueError("corpus snapshot document is invalid")
            document = item.get("document")
            chunks = item.get("chunks")
            if not isinstance(document, dict) or not isinstance(chunks, list):
                raise ValueError("corpus snapshot document is invalid")
            parser = document.get("parser")
            schema_version = document.get("schema_version")
            if not isinstance(parser, dict) or not isinstance(schema_version, str):
                raise ValueError("corpus snapshot parser identity is invalid")
            name = parser.get("name")
            version = parser.get("version")
            if not isinstance(name, str) or not isinstance(version, str):
                raise ValueError("corpus snapshot parser identity is invalid")
            parser_identities.add((name, version, schema_version))
            chunk_count += len(chunks)
        snapshot_id = value.get("snapshot_id")
        if not isinstance(snapshot_id, str) or not snapshot_id.startswith("sha256:"):
            raise ValueError("corpus snapshot identity is invalid")
        return {
            "byte_length": len(artifact.canonical_bytes),
            "canonical_sha256": hashlib.sha256(artifact.canonical_bytes).hexdigest(),
            "chunk_count": chunk_count,
            "document_count": len(documents),
            "generation_name": snapshot_id.removeprefix("sha256:"),
            "parser_identities": tuple(
                {
                    "name": name,
                    "schema_version": schema_version,
                    "version": version,
                }
                for name, version, schema_version in sorted(parser_identities)
            ),
            "rejection_count": len(rejections),
            "schema_version": "bijux.canon.ingest.corpus_publication.v1",
            "snapshot_id": snapshot_id,
        }

    def inspect_index(artifact_id: ArtifactID) -> dict[str, object]:
        artifact = store.load(artifact_id)
        if artifact.descriptor.schema_id == "index.lexical.v1":
            layout.operations_root.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(
                prefix=".lexical-inspection-",
                dir=layout.operations_root,
            ) as work:
                path = Path(work) / "lexical.sqlite"
                path.write_bytes(artifact.canonical_bytes)
                with SQLiteLexicalIndex(path) as lexical:
                    manifest = lexical.manifest
                    return {
                        "artifact_id": str(artifact_id),
                        "backend": "sqlite-fts5",
                        "chunk_count": manifest.chunk_count,
                        "chunk_set_sha256": manifest.chunk_set_sha256,
                        "generation_id": manifest.generation_id,
                        "schema_version": "bijux.canon.index.lexical_inspection.v1",
                        "segments": (
                            {
                                "backend": "sqlite-fts5",
                                "item_count": manifest.chunk_count,
                                "segment_generation_id": manifest.generation_id,
                            },
                        ),
                        "snapshot_artifact_id": (
                            str(artifact.descriptor.dependencies[0])
                            if len(artifact.descriptor.dependencies) == 1
                            else None
                        ),
                        "tokenizer": manifest.tokenizer,
                        "tokenizer_configuration_sha256": (
                            manifest.tokenizer_configuration_sha256
                        ),
                    }
        if artifact.descriptor.schema_id != "index.composite.v1":
            raise ValueError("artifact is not a supported index")
        archive = IndexGenerationArchive.from_bytes(artifact.canonical_bytes)
        report = index.admit_archive(archive.canonical_bytes)
        return asdict(report)

    return RuntimeApplicationServicesV2(
        jobs=jobs,
        inspector=inspector,
        corpus_inspector=inspect_corpus,
        index_inspector=inspect_index,
        retrieval_evaluator=PublicRetrievalEvaluator(
            installed_retrieval_evaluation.execute
        ).evaluate,
        operation_preflight=InstalledProfilePreflight(
            layout=layout,
            store=store,
            model_validator=embedding.validate,
        ),
        resource_closers=(embedding.close, index.close),
    )


__all__ = ["compose_runtime_application_services"]
