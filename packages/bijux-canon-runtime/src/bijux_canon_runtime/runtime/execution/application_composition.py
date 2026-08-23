# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Production composition root for the shared Runtime v2 application service."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import threading

from bijux_canon_index.application import IndexGenerationArchive, IndexService
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
from bijux_canon_runtime.runtime.inspection import RuntimeRunInspector
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
        self._lock = threading.Lock()

    @property
    def model_lock_id(self) -> str:
        return self._load().model_lock_id

    def embed(self, texts: Sequence[str]) -> EmbeddedBatch:
        return self._load().embed(texts)

    def _load(self) -> LocalEmbeddingModel:
        with self._lock:
            if self._model is None:
                lock = load_model_lock(self._model_root / "model.lock.json")
                self._model = LocalEmbeddingModel(self._model_root, lock)
            return self._model


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
    store = AtomicFilesystemArtifactPayloadStore(layout.cas_root)
    index = IndexService(layout.index_root)
    embedding = _LazyLocalEmbeddingModel(layout.model_root)
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
            ),
            CanonicalReasonOperationAdapter(),
            CanonicalAgentOperationAdapter(
                store=store,
                index=index,
                embedding=embedding,
                vex_store_root=layout.vex_root,
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
        layout.job_store_path,
        handlers=build_runtime_job_handlers(
            execute=execution.execute,
            replay=execute_replay,
        ),
        max_workers=max_workers,
    )
    inspector = RuntimeRunInspector(store)

    def inspect_corpus(artifact_id: ArtifactID) -> dict[str, object]:
        artifact = store.load(artifact_id)
        if artifact.descriptor.schema_id != "ingest.corpus-snapshot.v1":
            raise ValueError("artifact is not a corpus snapshot")
        value = json.loads(artifact.canonical_bytes)
        if not isinstance(value, dict) or not isinstance(value.get("documents"), list):
            raise ValueError("corpus snapshot payload is invalid")
        documents = value["documents"]
        assert isinstance(documents, list)
        snapshot_id = value.get("snapshot_id")
        if not isinstance(snapshot_id, str) or not snapshot_id.startswith("sha256:"):
            raise ValueError("corpus snapshot identity is invalid")
        return {
            "byte_length": len(artifact.canonical_bytes),
            "canonical_sha256": hashlib.sha256(artifact.canonical_bytes).hexdigest(),
            "generation_name": snapshot_id.removeprefix("sha256:"),
            "schema_version": "bijux.canon.ingest.corpus_publication.v1",
            "snapshot_id": snapshot_id,
        }

    def inspect_index(artifact_id: ArtifactID) -> dict[str, object]:
        artifact = store.load(artifact_id)
        if artifact.descriptor.schema_id != "index.composite.v1":
            raise ValueError("artifact is not a composite index")
        archive = IndexGenerationArchive.from_bytes(artifact.canonical_bytes)
        report = index.admit_archive(archive.canonical_bytes)
        return asdict(report)

    return RuntimeApplicationServicesV2(
        jobs=jobs,
        inspector=inspector,
        corpus_inspector=inspect_corpus,
        index_inspector=inspect_index,
    )


__all__ = ["compose_runtime_application_services"]
