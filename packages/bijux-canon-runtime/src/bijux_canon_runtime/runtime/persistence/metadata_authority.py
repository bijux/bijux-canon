# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Typed DuckDB authority for versioned Runtime metadata relationships."""

from __future__ import annotations

from dataclasses import astuple, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import duckdb

from bijux_canon_runtime.model.artifact import ImmutableArtifactDescriptor
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionStore,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, RunID, TenantID


class MetadataIntegrityError(ValueError):
    """Raised when metadata violates identity, history, or relationships."""


class AttemptStatus(StrEnum):
    """Durable execution-attempt states."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReferenceState(StrEnum):
    """Durable logical-reference states."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"


class CheckStatus(StrEnum):
    """Durable verification-check outcomes."""

    PASSED = "passed"
    FAILED = "failed"


class PublicationState(StrEnum):
    """Durable publication lifecycle states."""

    DRAFT = "draft"
    ADMITTED = "admitted"
    REVOKED = "revoked"


@dataclass(frozen=True, slots=True)
class RunRevisionRecord:
    """One immutable version of run state."""

    tenant_id: TenantID
    run_id: RunID
    revision: int
    state_hash: str
    payload_artifact_id: ArtifactID
    created_at: str


@dataclass(frozen=True, slots=True)
class RunDagRecord:
    """One immutable version of a run DAG."""

    tenant_id: TenantID
    run_id: RunID
    dag_version: int
    dag_hash: str
    payload_artifact_id: ArtifactID
    created_at: str


@dataclass(frozen=True, slots=True)
class RunAttemptRecord:
    """One append-only execution attempt."""

    tenant_id: TenantID
    run_id: RunID
    attempt_id: str
    step_index: int
    attempt_number: int
    status: AttemptStatus
    started_at: str
    finished_at: str | None = None
    failure_artifact_id: ArtifactID | None = None


@dataclass(frozen=True, slots=True)
class ArtifactReferenceRecord:
    """One versioned logical reference to immutable content."""

    tenant_id: TenantID
    run_id: RunID
    logical_artifact_id: str
    revision: int
    target_artifact_id: ArtifactID
    reference_state: ReferenceState
    created_at: str


@dataclass(frozen=True, slots=True)
class RunPolicyRecord:
    """A policy identity and its exact payload for one run."""

    tenant_id: TenantID
    run_id: RunID
    policy_kind: str
    policy_id: str
    payload_artifact_id: ArtifactID
    created_at: str


@dataclass(frozen=True, slots=True)
class RunCheckRecord:
    """A verification result backed by immutable evidence."""

    tenant_id: TenantID
    run_id: RunID
    check_id: str
    status: CheckStatus
    evidence_artifact_id: ArtifactID
    checked_at: str


@dataclass(frozen=True, slots=True)
class RunPublicationRecord:
    """One immutable revision of a run publication."""

    tenant_id: TenantID
    run_id: RunID
    publication_id: str
    revision: int
    publication_state: PublicationState
    selected_attempt_id: str
    manifest_artifact_id: ArtifactID
    receipt_artifact_id: ArtifactID
    stable_citation: str
    created_at: str


class DuckDBMetadataAuthority:
    """Validate and persist typed metadata beside the execution journal."""

    def __init__(self, path: Path) -> None:
        self._store = DuckDBExecutionStore(path)
        self._connection = self._store._connection

    def close(self) -> None:
        """Close the database and release its single-writer lock."""
        self._store.close()

    def __enter__(self) -> DuckDBMetadataAuthority:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def register_payload(
        self,
        descriptor: ImmutableArtifactDescriptor,
        *,
        created_at: str,
    ) -> None:
        """Register durable payload metadata and its dependency edges."""
        if not created_at:
            raise MetadataIntegrityError("payload created_at must not be empty")
        row = (
            str(descriptor.artifact_id),
            descriptor.schema_id,
            descriptor.media_type,
            descriptor.size_bytes,
            str(descriptor.payload_sha256),
            descriptor.producer,
        )
        existing = self._connection.execute(
            """
            SELECT artifact_id, schema_id, media_type, size_bytes,
                   payload_sha256, producer
            FROM artifact_payloads WHERE artifact_id = ?
            """,
            (str(descriptor.artifact_id),),
        ).fetchone()
        if existing is not None:
            if tuple(existing) != row:
                raise MetadataIntegrityError(
                    "immutable payload metadata conflicts with existing identity"
                )
            dependencies = {
                str(item)
                for (item,) in self._connection.execute(
                    """
                    SELECT dependency_artifact_id
                    FROM artifact_payload_dependencies
                    WHERE artifact_id = ?
                    """,
                    (str(descriptor.artifact_id),),
                ).fetchall()
            }
            if dependencies != {str(item) for item in descriptor.dependencies}:
                raise MetadataIntegrityError(
                    "immutable payload dependencies conflict with existing identity"
                )
            return

        self._connection.execute("BEGIN")
        try:
            self._connection.execute(
                """
                INSERT INTO artifact_payloads (
                    artifact_id, schema_id, media_type, size_bytes,
                    payload_sha256, producer, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (*row, created_at),
            )
            for dependency in descriptor.dependencies:
                self._connection.execute(
                    """
                    INSERT INTO artifact_payload_dependencies (
                        artifact_id, dependency_artifact_id
                    ) VALUES (?, ?)
                    """,
                    (str(descriptor.artifact_id), str(dependency)),
                )
            self._connection.execute("COMMIT")
        except Exception as exc:
            self._connection.execute("ROLLBACK")
            raise MetadataIntegrityError(
                "payload metadata references an unknown dependency"
            ) from exc

    def record_run_revision(self, record: RunRevisionRecord) -> None:
        self._insert_record(
            table="run_revisions",
            columns=(
                "tenant_id", "run_id", "revision", "state_hash",
                "payload_artifact_id", "created_at",
            ),
            key_columns=("tenant_id", "run_id", "revision"),
            values=astuple(record),
        )

    def record_dag(self, record: RunDagRecord) -> None:
        self._insert_record(
            table="run_dags",
            columns=(
                "tenant_id", "run_id", "dag_version", "dag_hash",
                "payload_artifact_id", "created_at",
            ),
            key_columns=("tenant_id", "run_id", "dag_version"),
            values=astuple(record),
        )

    def record_attempt(self, record: RunAttemptRecord) -> None:
        if record.status is AttemptStatus.RUNNING and record.finished_at is not None:
            raise MetadataIntegrityError("running attempt cannot have finished_at")
        if record.status is not AttemptStatus.RUNNING and record.finished_at is None:
            raise MetadataIntegrityError("terminal attempt requires finished_at")
        if record.status is AttemptStatus.FAILED and record.failure_artifact_id is None:
            raise MetadataIntegrityError("failed attempt requires failure artifact")
        self._insert_record(
            table="run_attempts",
            columns=(
                "tenant_id", "run_id", "attempt_id", "step_index",
                "attempt_number", "status", "started_at", "finished_at",
                "failure_artifact_id",
            ),
            key_columns=("tenant_id", "run_id", "attempt_id"),
            values=astuple(record),
        )

    def record_reference(self, record: ArtifactReferenceRecord) -> None:
        self._insert_record(
            table="artifact_references",
            columns=(
                "tenant_id", "run_id", "logical_artifact_id", "revision",
                "target_artifact_id", "reference_state", "created_at",
            ),
            key_columns=(
                "tenant_id", "run_id", "logical_artifact_id", "revision",
            ),
            values=astuple(record),
        )

    def record_policy(self, record: RunPolicyRecord) -> None:
        self._insert_record(
            table="run_policies",
            columns=(
                "tenant_id", "run_id", "policy_kind", "policy_id",
                "payload_artifact_id", "created_at",
            ),
            key_columns=("tenant_id", "run_id", "policy_kind", "policy_id"),
            values=astuple(record),
        )

    def record_check(self, record: RunCheckRecord) -> None:
        self._insert_record(
            table="run_checks",
            columns=(
                "tenant_id", "run_id", "check_id", "status",
                "evidence_artifact_id", "checked_at",
            ),
            key_columns=("tenant_id", "run_id", "check_id"),
            values=astuple(record),
        )

    def record_publication(self, record: RunPublicationRecord) -> None:
        if not record.stable_citation.strip():
            raise MetadataIntegrityError("publication citation must not be empty")
        self._insert_record(
            table="run_publications",
            columns=(
                "tenant_id", "run_id", "publication_id", "revision",
                "publication_state", "selected_attempt_id",
                "manifest_artifact_id", "receipt_artifact_id",
                "stable_citation", "created_at",
            ),
            key_columns=("tenant_id", "run_id", "publication_id", "revision"),
            values=astuple(record),
        )

    def counts(self, *, tenant_id: TenantID, run_id: RunID) -> dict[str, int]:
        """Return exact persisted relationship counts for inspection."""
        tables = (
            "run_revisions",
            "run_dags",
            "run_attempts",
            "artifact_references",
            "run_policies",
            "run_checks",
            "run_publications",
        )
        return {
            table: int(
                self._connection.execute(
                    f"SELECT count(*) FROM {table} WHERE tenant_id = ? AND run_id = ?",
                    (str(tenant_id), str(run_id)),
                ).fetchone()[0]
            )
            for table in tables
        }

    def _insert_record(
        self,
        *,
        table: str,
        columns: tuple[str, ...],
        key_columns: tuple[str, ...],
        values: tuple[Any, ...],
    ) -> None:
        normalized = tuple(
            item.value if isinstance(item, StrEnum) else str(item)
            if isinstance(item, str)
            else item
            for item in values
        )
        key_values = tuple(normalized[columns.index(key)] for key in key_columns)
        where = " AND ".join(f"{column} = ?" for column in key_columns)
        existing = self._connection.execute(
            f"SELECT {', '.join(columns)} FROM {table} WHERE {where}",
            key_values,
        ).fetchone()
        if existing is not None:
            if tuple(existing) != normalized:
                raise MetadataIntegrityError(
                    f"{table} identity conflicts with existing metadata"
                )
            return
        placeholders = ", ".join("?" for _ in columns)
        try:
            self._connection.execute(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                normalized,
            )
        except duckdb.Error as exc:
            raise MetadataIntegrityError(
                f"{table} references unknown or invalid metadata"
            ) from exc


__all__ = [
    "ArtifactReferenceRecord",
    "AttemptStatus",
    "CheckStatus",
    "DuckDBMetadataAuthority",
    "MetadataIntegrityError",
    "PublicationState",
    "ReferenceState",
    "RunAttemptRecord",
    "RunCheckRecord",
    "RunDagRecord",
    "RunPolicyRecord",
    "RunPublicationRecord",
    "RunRevisionRecord",
]
