# INTERNAL — NOT A PUBLIC EXTENSION POINT
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Profile-specific capability checks that run before durable submission."""

from __future__ import annotations

import importlib
from pathlib import Path
import tempfile

from bijux_canon_index.application import IndexGenerationArchive
from bijux_canon_index.domain.embedding import EmbeddingModelLock
from bijux_canon_index.infra.adapters.sqlite.lexical import SQLiteLexicalIndex
from bijux_canon_index.infra.adapters.sqlite.lexical import LexicalIndexError
from bijux_canon_index.infra.embeddings.model_cache import (
    ModelMaterializationError,
    load_model_lock,
    verify_materialized_model,
)
from bijux_canon_runtime.application.operations.service import (
    ApplicationCapabilityError,
)
from bijux_canon_runtime.application.runtime_configuration import RuntimeWorkspaceLayout
from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.model.execution.request_plan import (
    ExecutionProfile,
    RuntimeOperationRequest,
    RuntimeRequestOperation,
)
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.persistence.payload_store import ArtifactPayloadStore


class InstalledProfilePreflight:
    """Refuse unavailable model, backend, dimension, and index capabilities."""

    def __init__(
        self,
        *,
        layout: RuntimeWorkspaceLayout,
        store: ArtifactPayloadStore,
    ) -> None:
        self._layout = layout
        self._store = store

    def __call__(self, request: RuntimeOperationRequest) -> None:
        if request.execution_profile is ExecutionProfile.QDRANT_HYBRID:
            raise ApplicationCapabilityError(
                "profile qdrant-hybrid is not installed; configure and admit the "
                "Qdrant service capability or select a local profile"
            )
        if request.execution_profile is ExecutionProfile.OFFLINE_LEXICAL:
            self._preflight_lexical(request)
            return
        self._verify_local_dense_backend()
        lock = self._verified_model()
        if request.operation in {
            RuntimeRequestOperation.RETRIEVE,
            RuntimeRequestOperation.ASK,
            RuntimeRequestOperation.RESEARCH,
        }:
            if request.index_id is None:
                raise ApplicationCapabilityError(
                    "dense retrieval requires a composite index artifact"
                )
            artifact = self._load_contract(request.index_id, "index.composite.v1")
            try:
                archive = IndexGenerationArchive.from_bytes(artifact.canonical_bytes)
                self._layout.operations_root.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(
                    prefix=".profile-preflight-",
                    dir=self._layout.operations_root,
                ) as work:
                    with archive.materialize(Path(work) / "generation") as generation:
                        if generation.manifest.model_lock_artifact_id != lock.lock_id:
                            raise ApplicationCapabilityError(
                                "dense index model lock differs from the configured "
                                "model; restore that locked model or rebuild the index"
                            )
                        if (
                            generation.manifest.statistics.dimension
                            != lock.profile.dimension
                        ):
                            raise ApplicationCapabilityError(
                                "dense index dimension differs from the configured "
                                "model; rebuild the index with this model or restore "
                                "the matching model lock"
                            )
            except ApplicationCapabilityError:
                raise
            except (OSError, ValueError) as error:
                raise ApplicationCapabilityError(
                    "dense index backend or archive validation failed; install the "
                    "CPU-local dense profile and rebuild the index"
                ) from error

    def _preflight_lexical(self, request: RuntimeOperationRequest) -> None:
        if request.operation is RuntimeRequestOperation.INDEX_BUILD:
            if request.corpus_id is not None:
                self._load_contract(request.corpus_id, "ingest.corpus-snapshot.v1")
            return
        if request.operation is RuntimeRequestOperation.RUN:
            if request.corpus_id is not None:
                self._load_contract(request.corpus_id, "ingest.corpus-snapshot.v1")
            return
        if request.operation not in {
            RuntimeRequestOperation.RETRIEVE,
            RuntimeRequestOperation.ASK,
            RuntimeRequestOperation.RESEARCH,
        }:
            return
        if request.index_id is None:
            raise ApplicationCapabilityError(
                "offline lexical retrieval requires a lexical index artifact"
            )
        artifact = self._load_contract(request.index_id, "index.lexical.v1")
        dependencies = artifact.descriptor.dependencies
        if len(dependencies) != 1:
            raise ApplicationCapabilityError(
                "lexical index lacks one retained corpus snapshot; rebuild it from "
                "the durable corpus"
            )
        self._load_contract(dependencies[0], "ingest.corpus-snapshot.v1")
        self._layout.operations_root.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.TemporaryDirectory(
                prefix=".profile-preflight-",
                dir=self._layout.operations_root,
            ) as work:
                path = Path(work) / "lexical.sqlite"
                path.write_bytes(artifact.canonical_bytes)
                with SQLiteLexicalIndex(path):
                    pass
        except (LexicalIndexError, OSError, ValueError) as error:
            raise ApplicationCapabilityError(
                "lexical index validation failed; rebuild the offline lexical index"
            ) from error

    def _verified_model(self) -> EmbeddingModelLock:
        try:
            lock = load_model_lock(self._layout.model_lock_path)
            verify_materialized_model(self._layout.model_root, lock)
        except (ModelMaterializationError, OSError, ValueError) as error:
            raise ApplicationCapabilityError(
                "selected dense or hybrid profile requires a verified locked local "
                "embedding model; acquire or register the model and retry"
            ) from error
        return lock

    @staticmethod
    def _verify_local_dense_backend() -> None:
        try:
            faiss = importlib.import_module("faiss")
            required = (getattr(faiss, "IndexFlatIP"), getattr(faiss, "IndexHNSWFlat"))
        except (AttributeError, ImportError) as error:
            raise ApplicationCapabilityError(
                "selected dense or hybrid profile requires the CPU FAISS exact and "
                "HNSW backends; install the CPU-local dense profile and retry"
            ) from error
        if not all(callable(item) for item in required):
            raise ApplicationCapabilityError(
                "installed FAISS lacks required exact or HNSW backends; install the "
                "CPU-local dense profile and retry"
            )

    def _load_contract(
        self, artifact_id: ArtifactID, contract_id: str
    ) -> AddressedArtifact:
        try:
            artifact = self._store.load(artifact_id)
        except KeyError as error:
            raise ApplicationCapabilityError(
                f"required {contract_id} artifact is unavailable; create or restore it"
            ) from error
        if artifact.descriptor.schema_id != contract_id:
            raise ApplicationCapabilityError(
                f"selected profile requires {contract_id}; rebuild the matching index"
            )
        return artifact


__all__ = ["InstalledProfilePreflight"]
