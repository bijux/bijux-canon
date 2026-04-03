# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""Execution resources define the backend-facing surface area."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import NamedTuple

from bijux_vex.core.execution_result import ExecutionResult
from bijux_vex.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    ExecutionRequest,
    Result,
    Vector,
)


class BackendCapabilities(NamedTuple):
    contracts: set[object] | None = None
    max_vector_size: int | None = None
    metrics: set[str] | None = None
    deterministic_query: bool | None = None
    replayable: bool | None = None
    isolation_level: str | None = None
    ann_support: bool | None = None  # legacy
    supports_ann: bool | None = None


class ExecutionResources(NamedTuple):
    name: str
    vectors: VectorSource
    ledger: ExecutionLedger
    capabilities: BackendCapabilities | None = None


class VectorSource(ABC):
    """Provides documents, chunks, and vectors for execution without DB semantics."""

    @abstractmethod
    def put_document(self, tx: Tx, document: Document) -> None:
        """Insert or replace a document."""

    @abstractmethod
    def get_document(self, document_id: str) -> Document | None:
        """Return a document by ID or None if absent."""

    @abstractmethod
    def list_documents(self) -> Iterable[Document]:
        """List documents deterministically."""

    @abstractmethod
    def delete_document(self, tx: Tx, document_id: str) -> None:
        """Remove a document and associated chunk content atomically."""

    @abstractmethod
    def put_chunk(self, tx: Tx, chunk: Chunk) -> None:
        """Insert or replace a chunk record."""

    @abstractmethod
    def get_chunk(self, chunk_id: str) -> Chunk | None:
        """Return a chunk by ID or None."""

    @abstractmethod
    def list_chunks(self, document_id: str | None = None) -> Iterable[Chunk]:
        """List chunks, optionally filtered by document_id; ordering must be deterministic."""

    @abstractmethod
    def delete_chunk(self, tx: Tx, chunk_id: str) -> None:
        """Remove a chunk record."""

    @abstractmethod
    def put_vector(self, tx: Tx, vector: Vector) -> None:
        """Insert or replace a vector (allowed only during ingest/materialization phases)."""

    @abstractmethod
    def get_vector(self, vector_id: str) -> Vector | None:
        """Return a vector by ID or None."""

    @abstractmethod
    def list_vectors(self, chunk_id: str | None = None) -> Iterable[Vector]:
        """List vectors deterministically, optionally filtered by chunk_id."""

    @abstractmethod
    def query(self, artifact_id: str, request: ExecutionRequest) -> Iterable[Result]:
        """
        Evaluate an execution request against a given artifact.
        Must honor determinism rules including tie-break ordering and is only valid for deterministic contracts.
        """

    @abstractmethod
    def delete_vector(self, tx: Tx, vector_id: str) -> None:
        """Remove a vector."""


class ExecutionLedger(ABC):
    """Registers execution artifacts and connects them to vector sets without implying database semantics."""

    @abstractmethod
    def put_artifact(self, tx: Tx, artifact: ExecutionArtifact) -> None:
        """Insert or replace an execution artifact; must be atomic with related vector metadata if applicable."""

    @abstractmethod
    def get_artifact(self, artifact_id: str) -> ExecutionArtifact | None:
        """Return an execution artifact by ID or None."""

    @abstractmethod
    def list_artifacts(self) -> Iterable[ExecutionArtifact]:
        """List execution artifacts deterministically."""

    @abstractmethod
    def delete_artifact(self, tx: Tx, artifact_id: str) -> None:
        """Remove an execution artifact."""

    @abstractmethod
    def put_execution_result(self, tx: Tx, result: ExecutionResult) -> None:
        """Persist a completed execution result keyed by execution_id/signature."""

    @abstractmethod
    def get_execution_result(self, execution_id: str) -> ExecutionResult | None:
        """Load a previously persisted execution result."""

    @abstractmethod
    def latest_execution_result(self, artifact_id: str) -> ExecutionResult | None:
        """Return the most recent execution result for an artifact if known."""


# Local import to avoid circular type checking at runtime
from bijux_vex.contracts.tx import Tx  # noqa: E402
