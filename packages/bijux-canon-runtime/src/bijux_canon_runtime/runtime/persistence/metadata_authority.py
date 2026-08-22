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


@dataclass(frozen=True, slots=True)
class PublicationTransactionRecord:
    """Durable publication intent and its recovery state."""

    tenant_id: TenantID
    run_id: RunID
    transaction_id: str
    intent_hash: str
    intent_json: str
    status: str
    failure_reason: str | None
    created_at: str
    completed_at: str | None


class DuckDBMetadataAuthority:
    """Validate and persist typed metadata beside the execution journal."""

    def __init__(self, path: Path, *, lock_timeout_seconds: float = 5.0) -> None:
        self._store = DuckDBExecutionStore(
            path,
            lock_timeout_seconds=lock_timeout_seconds,
        )
        self._connection = self._store._connection

    def close(self) -> None:
        """Close the database and release its single-writer lock."""
        self._store.close()

    def __enter__(self) -> DuckDBMetadataAuthority:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def prepare_publication_transaction(
        self,
        *,
        tenant_id: TenantID,
        run_id: RunID,
        transaction_id: str,
        intent_hash: str,
        intent_json: str,
        created_at: str,
    ) -> PublicationTransactionRecord:
        """Durably record publication intent after all blobs are verified."""
        existing = self.publication_transaction(
            tenant_id=tenant_id,
            run_id=run_id,
            transaction_id=transaction_id,
            required=False,
        )
        if existing is not None:
            if (
                existing.intent_hash != intent_hash
                or existing.intent_json != intent_json
            ):
                raise MetadataIntegrityError(
                    "publication transaction identity has conflicting intent"
                )
            return existing
        try:
            self._connection.execute(
                """
                INSERT INTO publication_transactions (
                    tenant_id, run_id, transaction_id, intent_hash, intent_json,
                    status, failure_reason, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, 'prepared', NULL, ?, NULL)
                """,
                (
                    str(tenant_id),
                    str(run_id),
                    transaction_id,
                    intent_hash,
                    intent_json,
                    created_at,
                ),
            )
        except duckdb.Error as exc:
            raise MetadataIntegrityError(
                "publication transaction references an unknown run"
            ) from exc
        record = self.publication_transaction(
            tenant_id=tenant_id,
            run_id=run_id,
            transaction_id=transaction_id,
        )
        assert record is not None
        return record

    def publication_transaction(
        self,
        *,
        tenant_id: TenantID,
        run_id: RunID,
        transaction_id: str,
        required: bool = True,
    ) -> PublicationTransactionRecord | None:
        """Read one transaction without interpreting its intent payload."""
        row = self._connection.execute(
            """
            SELECT tenant_id, run_id, transaction_id, intent_hash, intent_json,
                   status, failure_reason, created_at, completed_at
            FROM publication_transactions
            WHERE tenant_id = ? AND run_id = ? AND transaction_id = ?
            """,
            (str(tenant_id), str(run_id), transaction_id),
        ).fetchone()
        if row is None:
            if required:
                raise MetadataIntegrityError("publication transaction not found")
            return None
        return PublicationTransactionRecord(
            tenant_id=TenantID(row[0]),
            run_id=RunID(row[1]),
            transaction_id=row[2],
            intent_hash=row[3],
            intent_json=row[4],
            status=row[5],
            failure_reason=row[6],
            created_at=row[7],
            completed_at=row[8],
        )

    def commit_prepared_publication(
        self,
        *,
        transaction: PublicationTransactionRecord,
        references: tuple[ArtifactReferenceRecord, ...],
        completed_at: str,
    ) -> PublicationTransactionRecord:
        """Atomically activate references and mark their intent committed."""
        current = self.publication_transaction(
            tenant_id=transaction.tenant_id,
            run_id=transaction.run_id,
            transaction_id=transaction.transaction_id,
        )
        assert current is not None
        if current.intent_hash != transaction.intent_hash:
            raise MetadataIntegrityError("publication transaction intent changed")
        if current.status == "aborted":
            raise MetadataIntegrityError("aborted publication cannot be committed")
        if current.status == "committed":
            self._assert_transaction_artifacts(current, references)
            return current

        self._connection.execute("BEGIN")
        try:
            for reference in references:
                self._activate_reference(current, reference)
                self._connection.execute(
                    """
                    INSERT INTO publication_transaction_artifacts (
                        tenant_id, run_id, transaction_id, logical_artifact_id,
                        revision, target_artifact_id
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(current.tenant_id),
                        str(current.run_id),
                        current.transaction_id,
                        reference.logical_artifact_id,
                        reference.revision,
                        str(reference.target_artifact_id),
                    ),
                )
            self._connection.execute(
                """
                UPDATE publication_transactions
                SET status = 'committed', completed_at = ?
                WHERE tenant_id = ? AND run_id = ? AND transaction_id = ?
                  AND status = 'prepared'
                """,
                (
                    completed_at,
                    str(current.tenant_id),
                    str(current.run_id),
                    current.transaction_id,
                ),
            )
            self._connection.execute("COMMIT")
        except Exception as exc:
            self._connection.execute("ROLLBACK")
            raise MetadataIntegrityError(
                "publication activation violated metadata integrity"
            ) from exc
        committed = self.publication_transaction(
            tenant_id=current.tenant_id,
            run_id=current.run_id,
            transaction_id=current.transaction_id,
        )
        assert committed is not None
        return committed

    def abort_prepared_publication(
        self,
        *,
        transaction: PublicationTransactionRecord,
        failure_reason: str,
        completed_at: str,
    ) -> PublicationTransactionRecord:
        """Durably classify an unrecoverable prepared transaction."""
        if not failure_reason.strip():
            raise MetadataIntegrityError("publication failure reason must not be empty")
        self._connection.execute(
            """
            UPDATE publication_transactions
            SET status = 'aborted', failure_reason = ?, completed_at = ?
            WHERE tenant_id = ? AND run_id = ? AND transaction_id = ?
              AND status = 'prepared'
            """,
            (
                failure_reason,
                completed_at,
                str(transaction.tenant_id),
                str(transaction.run_id),
                transaction.transaction_id,
            ),
        )
        record = self.publication_transaction(
            tenant_id=transaction.tenant_id,
            run_id=transaction.run_id,
            transaction_id=transaction.transaction_id,
        )
        assert record is not None
        return record

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
                "tenant_id",
                "run_id",
                "revision",
                "state_hash",
                "payload_artifact_id",
                "created_at",
            ),
            key_columns=("tenant_id", "run_id", "revision"),
            values=astuple(record),
        )

    def record_dag(self, record: RunDagRecord) -> None:
        self._insert_record(
            table="run_dags",
            columns=(
                "tenant_id",
                "run_id",
                "dag_version",
                "dag_hash",
                "payload_artifact_id",
                "created_at",
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
                "tenant_id",
                "run_id",
                "attempt_id",
                "step_index",
                "attempt_number",
                "status",
                "started_at",
                "finished_at",
                "failure_artifact_id",
            ),
            key_columns=("tenant_id", "run_id", "attempt_id"),
            values=astuple(record),
        )

    def record_reference(self, record: ArtifactReferenceRecord) -> None:
        self._insert_record(
            table="artifact_references",
            columns=(
                "tenant_id",
                "run_id",
                "logical_artifact_id",
                "revision",
                "target_artifact_id",
                "reference_state",
                "created_at",
            ),
            key_columns=(
                "tenant_id",
                "run_id",
                "logical_artifact_id",
                "revision",
            ),
            values=astuple(record),
        )

    def record_policy(self, record: RunPolicyRecord) -> None:
        self._insert_record(
            table="run_policies",
            columns=(
                "tenant_id",
                "run_id",
                "policy_kind",
                "policy_id",
                "payload_artifact_id",
                "created_at",
            ),
            key_columns=("tenant_id", "run_id", "policy_kind", "policy_id"),
            values=astuple(record),
        )

    def record_check(self, record: RunCheckRecord) -> None:
        self._insert_record(
            table="run_checks",
            columns=(
                "tenant_id",
                "run_id",
                "check_id",
                "status",
                "evidence_artifact_id",
                "checked_at",
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
                "tenant_id",
                "run_id",
                "publication_id",
                "revision",
                "publication_state",
                "selected_attempt_id",
                "manifest_artifact_id",
                "receipt_artifact_id",
                "stable_citation",
                "created_at",
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
        counts: dict[str, int] = {}
        for table in tables:
            row = self._connection.execute(
                f"SELECT count(*) FROM {table} WHERE tenant_id = ? AND run_id = ?",
                (str(tenant_id), str(run_id)),
            ).fetchone()
            if row is None:
                raise MetadataIntegrityError(f"count query returned no row for {table}")
            counts[table] = int(row[0])
        return counts

    def _activate_reference(
        self,
        transaction: PublicationTransactionRecord,
        reference: ArtifactReferenceRecord,
    ) -> None:
        if (
            reference.tenant_id != transaction.tenant_id
            or reference.run_id != transaction.run_id
            or reference.reference_state is not ReferenceState.ACTIVE
        ):
            raise MetadataIntegrityError(
                "publication reference is outside its transaction scope"
            )
        existing = self._connection.execute(
            """
            SELECT target_artifact_id, reference_state, created_at
            FROM artifact_references
            WHERE tenant_id = ? AND run_id = ?
              AND logical_artifact_id = ? AND revision = ?
            """,
            (
                str(reference.tenant_id),
                str(reference.run_id),
                reference.logical_artifact_id,
                reference.revision,
            ),
        ).fetchone()
        expected = (
            str(reference.target_artifact_id),
            reference.reference_state.value,
            reference.created_at,
        )
        if existing is not None:
            if tuple(existing) != expected:
                raise MetadataIntegrityError(
                    "logical reference revision has conflicting target"
                )
            raise MetadataIntegrityError(
                "logical reference revision was activated by another transaction"
            )
        active = self._connection.execute(
            """
            SELECT revision FROM artifact_references
            WHERE tenant_id = ? AND run_id = ? AND logical_artifact_id = ?
              AND reference_state = 'active'
            ORDER BY revision DESC
            """,
            (
                str(reference.tenant_id),
                str(reference.run_id),
                reference.logical_artifact_id,
            ),
        ).fetchall()
        if len(active) > 1:
            raise MetadataIntegrityError("logical reference has split-brain activation")
        if active:
            active_revision = int(active[0][0])
            if reference.revision != active_revision + 1:
                raise MetadataIntegrityError(
                    "logical reference revision must advance exactly once"
                )
            self._connection.execute(
                """
                UPDATE artifact_references SET reference_state = 'superseded'
                WHERE tenant_id = ? AND run_id = ?
                  AND logical_artifact_id = ? AND revision = ?
                """,
                (
                    str(reference.tenant_id),
                    str(reference.run_id),
                    reference.logical_artifact_id,
                    active_revision,
                ),
            )
        elif reference.revision != 0:
            raise MetadataIntegrityError(
                "first logical reference revision must be zero"
            )
        self._connection.execute(
            """
            INSERT INTO artifact_references (
                tenant_id, run_id, logical_artifact_id, revision,
                target_artifact_id, reference_state, created_at
            ) VALUES (?, ?, ?, ?, ?, 'active', ?)
            """,
            (
                str(reference.tenant_id),
                str(reference.run_id),
                reference.logical_artifact_id,
                reference.revision,
                str(reference.target_artifact_id),
                reference.created_at,
            ),
        )

    def _assert_transaction_artifacts(
        self,
        transaction: PublicationTransactionRecord,
        references: tuple[ArtifactReferenceRecord, ...],
    ) -> None:
        actual = {
            (logical_id, int(revision), target_id)
            for logical_id, revision, target_id in self._connection.execute(
                """
                SELECT logical_artifact_id, revision, target_artifact_id
                FROM publication_transaction_artifacts
                WHERE tenant_id = ? AND run_id = ? AND transaction_id = ?
                """,
                (
                    str(transaction.tenant_id),
                    str(transaction.run_id),
                    transaction.transaction_id,
                ),
            ).fetchall()
        }
        expected = {
            (
                reference.logical_artifact_id,
                reference.revision,
                str(reference.target_artifact_id),
            )
            for reference in references
        }
        if actual != expected:
            raise MetadataIntegrityError(
                "committed publication transaction artifacts do not match intent"
            )

    def _insert_record(
        self,
        *,
        table: str,
        columns: tuple[str, ...],
        key_columns: tuple[str, ...],
        values: tuple[Any, ...],
    ) -> None:
        normalized = tuple(
            item.value
            if isinstance(item, StrEnum)
            else str(item)
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
    "PublicationTransactionRecord",
    "PublicationState",
    "ReferenceState",
    "RunAttemptRecord",
    "RunCheckRecord",
    "RunDagRecord",
    "RunPolicyRecord",
    "RunPublicationRecord",
    "RunRevisionRecord",
]
