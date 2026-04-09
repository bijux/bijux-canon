# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Backend helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import NamedTuple

from bijux_canon_index.contracts.authz import AllowAllAuthz, Authz
from bijux_canon_index.contracts.resources import (
    BackendCapabilities,
    ExecutionLedger,
    ExecutionResources,
    VectorSource,
)
from bijux_canon_index.contracts.tx import Tx
from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.errors import (
    AtomicityViolationError,
    InvariantError,
    NotFoundError,
    ValidationError,
)
from bijux_canon_index.core.execution_result import ExecutionResult
from bijux_canon_index.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    ExecutionRequest,
    Result,
    Vector,
)
from bijux_canon_index.domain.provenance.audit import AuditRecord
from bijux_canon_index.domain.requests import scoring
from bijux_canon_index.infra.adapters.ann_base import AnnExecutionRequestRunner


class MemoryState:
    """Represents memory state."""

    def __init__(self) -> None:
        """Initialize the instance."""
        self.documents: dict[str, Document] = {}
        self.chunks: dict[str, Chunk] = {}
        self.vectors: dict[str, Vector] = {}
        self.artifacts: dict[str, ExecutionArtifact] = {}
        self.execution_results: dict[str, ExecutionResult] = {}
        self.last_result_by_artifact: dict[str, ExecutionResult] = {}
        self.results_by_artifact: dict[str, list[str]] = {}
        self.audit_log: list[AuditRecord] = []
        self._tx_counter = 0
        self.in_tx = False

    def next_tx_id(self) -> str:
        """Handle next tx ID."""
        self._tx_counter += 1
        return f"tx-{self._tx_counter}"

    @property
    def last_hash(self) -> str | None:
        """Handle last hash."""
        return self.audit_log[-1].record_hash if self.audit_log else None

    def append_audit(self, record: AuditRecord) -> None:
        """Handle append audit."""
        self.audit_log.append(record)

    def compact_audit(self, retention: int) -> None:
        """Handle compact audit."""
        if retention < 0:
            raise ValueError("retention must be non-negative")
        if len(self.audit_log) > retention:
            self.audit_log = self.audit_log[-retention:]


class MemoryTx(Tx):
    """Represents memory tx."""

    def __init__(
        self,
        state: MemoryState,
        audit_builder: Callable[[str, str | None, list[str]], AuditRecord],
    ) -> None:
        """Initialize the instance."""
        self._state = state
        self._audit_builder = audit_builder
        self._tx_id = state.next_tx_id()
        self._doc_writes: dict[str, Document] = {}
        self._doc_deletes: set[str] = set()
        self._chunk_writes: dict[str, Chunk] = {}
        self._chunk_deletes: set[str] = set()
        self._vector_writes: dict[str, Vector] = {}
        self._vector_deletes: set[str] = set()
        self._artifact_writes: dict[str, ExecutionArtifact] = {}
        self._artifact_deletes: set[str] = set()
        self._result_writes: dict[str, ExecutionResult] = {}
        self._result_deletes: set[str] = set()
        self._active = True
        self._entered = False

    @property
    def tx_id(self) -> str:
        """Handle tx ID."""
        return self._tx_id

    def __enter__(self) -> Tx:
        """Enter the managed context."""
        if self._state.in_tx:
            raise AtomicityViolationError(message="Nested Tx is not allowed")
        self._state.in_tx = True
        self._entered = True
        return self

    def stage_document(self, document: Document) -> None:
        """Handle stage document."""
        self._doc_writes[document.document_id] = document
        self._doc_deletes.discard(document.document_id)

    def delete_document(self, document_id: str) -> None:
        """Handle delete document."""
        self._doc_deletes.add(document_id)
        self._doc_writes.pop(document_id, None)

    def stage_chunk(self, chunk: Chunk) -> None:
        """Handle stage chunk."""
        self._chunk_writes[chunk.chunk_id] = chunk
        self._chunk_deletes.discard(chunk.chunk_id)

    def delete_chunk(self, chunk_id: str) -> None:
        """Handle delete chunk."""
        self._chunk_deletes.add(chunk_id)
        self._chunk_writes.pop(chunk_id, None)

    def stage_vector(self, vector: Vector) -> None:
        """Handle stage vector."""
        self._vector_writes[vector.vector_id] = vector
        self._vector_deletes.discard(vector.vector_id)

    def delete_vector(self, vector_id: str) -> None:
        """Handle delete vector."""
        self._vector_deletes.add(vector_id)
        self._vector_writes.pop(vector_id, None)

    def stage_artifact(self, artifact: ExecutionArtifact) -> None:
        """Handle stage artifact."""
        self._artifact_writes[artifact.artifact_id] = artifact
        self._artifact_deletes.discard(artifact.artifact_id)

    def delete_artifact(self, artifact_id: str) -> None:
        """Handle delete artifact."""
        self._artifact_deletes.add(artifact_id)
        self._artifact_writes.pop(artifact_id, None)
        self._result_deletes.add(artifact_id)
        self._result_writes.pop(artifact_id, None)

    def commit(self) -> None:
        """Handle commit."""
        if not self._entered:
            raise AtomicityViolationError(message="Tx must be entered before commit")
        if not self._active:
            raise AtomicityViolationError(message="Tx already finished")
        self._apply_document_changes()
        self._apply_chunk_changes()
        self._apply_vector_changes()
        self._apply_artifact_changes()
        self._apply_result_changes()
        actions = self._changes_summary()
        record = self._audit_builder(self.tx_id, self._state.last_hash, actions)
        self._state.append_audit(record)
        self._state.in_tx = False
        self._active = False

    def _apply_document_changes(self) -> None:
        """Handle apply document changes."""
        for document_id in self._doc_deletes:
            self._state.documents.pop(document_id, None)
        self._state.documents.update(self._doc_writes)

    def _apply_chunk_changes(self) -> None:
        """Handle apply chunk changes."""
        for chunk_id in self._chunk_deletes:
            self._state.chunks.pop(chunk_id, None)
        self._state.chunks.update(self._chunk_writes)

    def _apply_vector_changes(self) -> None:
        """Handle apply vector changes."""
        for vector_id in self._vector_deletes:
            self._state.vectors.pop(vector_id, None)
        self._state.vectors.update(self._vector_writes)

    def _apply_artifact_changes(self) -> None:
        """Handle apply artifact changes."""
        for artifact_id in self._artifact_deletes:
            self._state.artifacts.pop(artifact_id, None)
            self._state.results_by_artifact.pop(artifact_id, None)
            to_purge = [
                rid
                for rid, res in self._state.execution_results.items()
                if res.artifact_id == artifact_id
            ]
            for rid in to_purge:
                self._state.execution_results.pop(rid, None)
        self._state.artifacts.update(self._artifact_writes)

    def _apply_result_changes(self) -> None:
        """Handle apply result changes."""
        for execution_id in self._result_deletes:
            self._state.execution_results.pop(execution_id, None)
        self._state.execution_results.update(self._result_writes)
        for res in self._result_writes.values():
            art_id = res.artifact_id
            history = self._state.results_by_artifact.setdefault(art_id, [])
            history.append(res.execution_id)
            max_keep = 5
            while len(history) > max_keep:
                oldest = history.pop(0)
                self._state.execution_results.pop(oldest, None)
            self._state.last_result_by_artifact[art_id] = res

    def _changes_summary(self) -> list[str]:
        """Handle changes summary."""
        actions: list[str] = []
        if self._doc_writes or self._doc_deletes:
            actions.append("documents")
        if self._chunk_writes or self._chunk_deletes:
            actions.append("chunks")
        if self._vector_writes or self._vector_deletes:
            actions.append("vectors")
        if self._artifact_writes or self._artifact_deletes:
            actions.append("artifacts")
        if self._result_writes or self._result_deletes:
            actions.append("execution_results")
        return actions
        self._state.in_tx = False
        return None

    def abort(self) -> None:
        """Handle abort."""
        if not self._entered:
            raise AtomicityViolationError(message="Tx must be entered before abort")
        if not self._active:
            raise AtomicityViolationError(message="Tx already finished")
        self._active = False
        self._state.in_tx = False


def _as_memory_tx(tx: Tx) -> MemoryTx:
    """Coerce to memory tx."""
    if not isinstance(tx, MemoryTx):
        raise TypeError("MemoryTx required")
    return tx


class MemoryVectorSource(VectorSource):
    """Represents memory vector source."""

    def __init__(self, state: MemoryState):
        """Initialize the instance."""
        self._state = state

    # Document operations
    def put_document(self, tx: Tx, document: Document) -> None:
        """Handle put document."""
        memory_tx = _as_memory_tx(tx)
        memory_tx.stage_document(document)

    def get_document(self, document_id: str) -> Document | None:
        """Return document."""
        return self._state.documents.get(document_id)

    def list_documents(self) -> Iterable[Document]:
        """List documents."""
        return sorted(self._state.documents.values(), key=lambda d: d.document_id)

    def delete_document(self, tx: Tx, document_id: str) -> None:
        """Handle delete document."""
        memory_tx = _as_memory_tx(tx)
        memory_tx.delete_document(document_id)

    # Chunk operations
    def put_chunk(self, tx: Tx, chunk: Chunk) -> None:
        """Handle put chunk."""
        memory_tx = _as_memory_tx(tx)
        memory_tx.stage_chunk(chunk)

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        """Return chunk."""
        return self._state.chunks.get(chunk_id)

    def list_chunks(self, document_id: str | None = None) -> Iterable[Chunk]:
        """List chunks."""
        chunks: list[Chunk] = list(self._state.chunks.values())
        if document_id:
            chunks = [c for c in chunks if c.document_id == document_id]
        return sorted(chunks, key=lambda c: c.chunk_id)

    def delete_chunk(self, tx: Tx, chunk_id: str) -> None:
        """Handle delete chunk."""
        memory_tx = _as_memory_tx(tx)
        memory_tx.delete_chunk(chunk_id)

    def put_vector(self, tx: Tx, vector: Vector) -> None:
        """Handle put vector."""
        memory_tx = _as_memory_tx(tx)
        memory_tx.stage_vector(vector)

    def get_vector(self, vector_id: str) -> Vector | None:
        """Return vector."""
        return self._state.vectors.get(vector_id)

    def list_vectors(self, chunk_id: str | None = None) -> Iterable[Vector]:
        """List vectors."""
        vectors: list[Vector] = list(self._state.vectors.values())
        if chunk_id:
            vectors = [v for v in vectors if v.chunk_id == chunk_id]
        return sorted(vectors, key=lambda v: v.vector_id)

    def query(self, artifact_id: str, request: ExecutionRequest) -> Iterable[Result]:
        """Query artifact ID."""
        if request.vector is None:
            raise ValidationError(message="execution vector required")
        artifact = self._state.artifacts.get(artifact_id)
        if artifact is None:
            raise NotFoundError(message=f"Execution artifact {artifact_id} not found")
        if artifact.execution_contract is not request.execution_contract:
            raise InvariantError(
                message="Execution contract does not match artifact execution contract"
            )
        query_vec = request.vector
        scored: list[Result] = []
        for vector in self._state.vectors.values():
            if len(query_vec) != vector.dimension:
                continue
            score = scoring.score(artifact.metric, query_vec, vector.values)
            chunk = self._state.chunks.get(vector.chunk_id)
            document_id = chunk.document_id if chunk else ""
            scored.append(
                Result(
                    request_id=request.request_id,
                    document_id=document_id,
                    chunk_id=vector.chunk_id,
                    vector_id=vector.vector_id,
                    artifact_id=artifact_id,
                    score=score,
                    rank=0,
                )
            )
        scored.sort(key=scoring.tie_break_key)
        limited = scored[: request.top_k]
        for idx, res in enumerate(limited, start=1):
            limited[idx - 1] = Result(
                request_id=res.request_id,
                document_id=res.document_id,
                chunk_id=res.chunk_id,
                vector_id=res.vector_id,
                artifact_id=res.artifact_id,
                score=res.score,
                rank=idx,
            )
        return limited

    def delete_vector(self, tx: Tx, vector_id: str) -> None:
        """Handle delete vector."""
        memory_tx = _as_memory_tx(tx)
        memory_tx.delete_vector(vector_id)


class MemoryExecutionLedger(ExecutionLedger):
    """Represents memory execution ledger."""

    MAX_ARTIFACTS = 1000
    MAX_RESULTS = 5000

    def __init__(self, state: MemoryState):
        """Initialize the instance."""
        self._state = state

    def put_artifact(self, tx: Tx, artifact: ExecutionArtifact) -> None:
        """Handle put artifact."""
        existing = self._state.artifacts.get(artifact.artifact_id)
        if existing and existing.execution_contract is not artifact.execution_contract:
            raise InvariantError(
                message="Cannot overwrite artifact with different execution contract"
            )
        if existing is None and len(self._state.artifacts) >= self.MAX_ARTIFACTS:
            raise InvariantError(
                message="Artifact retention limit exceeded; compact or delete artifacts"
            )
        memory_tx = _as_memory_tx(tx)
        memory_tx.stage_artifact(artifact)

    def get_artifact(self, artifact_id: str) -> ExecutionArtifact | None:
        """Return artifact."""
        return self._state.artifacts.get(artifact_id)

    def list_artifacts(self) -> Iterable[ExecutionArtifact]:
        """List artifacts."""
        return sorted(self._state.artifacts.values(), key=lambda a: a.artifact_id)

    def delete_artifact(self, tx: Tx, artifact_id: str) -> None:
        """Handle delete artifact."""
        memory_tx = _as_memory_tx(tx)
        memory_tx.delete_artifact(artifact_id)

    def put_execution_result(self, tx: Tx, result: ExecutionResult) -> None:
        """Handle put execution result."""
        if (
            result.execution_id not in self._state.execution_results
            and len(self._state.execution_results) >= self.MAX_RESULTS
        ):
            raise InvariantError(
                message="Execution result retention limit exceeded; compact or delete execution results"
            )
        memory_tx = _as_memory_tx(tx)
        memory_tx._result_writes[result.execution_id] = result
        memory_tx._result_deletes.discard(result.execution_id)

    def get_execution_result(self, execution_id: str) -> ExecutionResult | None:
        """Return execution result."""
        return self._state.execution_results.get(execution_id)

    def latest_execution_result(self, artifact_id: str) -> ExecutionResult | None:
        """Handle latest execution result."""
        return self._state.last_result_by_artifact.get(artifact_id)


class MemoryFixture(NamedTuple):
    """Represents memory fixture."""

    tx_factory: Callable[[], MemoryTx]
    stores: ExecutionResources
    authz: Authz
    name: str
    ann: AnnExecutionRequestRunner | None = None
    diagnostics: dict[str, Callable[[], object]] | None = None


def _build_audit(
    record_id: str, prev_hash: str | None, actions: list[str]
) -> AuditRecord:
    """Build audit."""
    details = tuple((str(i), action) for i, action in enumerate(actions))
    return AuditRecord(
        record_id=record_id,
        tx_id=record_id,
        action="commit",
        resource_type="tx",
        resource_id=record_id,
        actor=None,
        prev_hash=prev_hash,
        details=details,
    )


def memory_backend() -> MemoryFixture:
    """Handle memory backend."""
    state = MemoryState()

    def tx_factory() -> MemoryTx:
        """Handle tx factory."""
        return MemoryTx(state, _build_audit)

    capabilities = BackendCapabilities(
        contracts={
            ExecutionContract.DETERMINISTIC,
            ExecutionContract.NON_DETERMINISTIC,
        },
        max_vector_size=1024,
        metrics={"l2"},
        deterministic_query=True,
        replayable=True,
        isolation_level="process",
        ann_support=True,
        supports_ann=True,
    )
    stores = ExecutionResources(
        name="memory",
        vectors=MemoryVectorSource(state),
        ledger=MemoryExecutionLedger(state),
        capabilities=capabilities,
    )
    authz: Authz = AllowAllAuthz()
    diagnostics = {
        "health_check": lambda: {"status": "ok", "engine": "memory"},
        "capacity": lambda: {
            "documents": len(state.documents),
            "chunks": len(state.chunks),
            "vectors": len(state.vectors),
        },
        "corruption_check": lambda: (),
    }
    fixture = MemoryFixture(
        tx_factory=tx_factory,
        stores=stores,
        authz=authz,
        name="memory",
        ann=None,
        diagnostics=diagnostics,
    )
    try:
        from bijux_canon_index.infra.adapters.ann_hnsw import HnswAnnRunner

        fixture = fixture._replace(ann=HnswAnnRunner(stores.vectors))
    except Exception:
        try:
            from bijux_canon_index.infra.adapters.ann_reference import (
                ReferenceAnnRunner,
            )

            fixture = fixture._replace(ann=ReferenceAnnRunner(stores.vectors))
        except Exception:
            fixture = fixture._replace(ann=None)
    return fixture
