# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Stable path-free inspection of immutable Runtime artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

import duckdb

from bijux_canon_runtime.model.artifact import (
    ImmutableArtifactDescriptor,
    canonical_json_bytes,
)
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionStore,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, RunID, TenantID
from bijux_canon_runtime.runtime.pagination import PageRequest, paginate_collections
from bijux_canon_runtime.runtime.persistence.filesystem_payload_store import (
    AtomicFilesystemArtifactPayloadStore,
    PayloadCorruptionError,
)
from bijux_canon_runtime.runtime.persistence.reachability import (
    ArtifactReachabilityReport,
    ArtifactReachabilityValidator,
)


@dataclass(frozen=True, slots=True)
class ArtifactReferenceView:
    """One immutable logical-reference revision without storage locations."""

    tenant_id: TenantID
    run_id: RunID
    logical_artifact_id: str
    revision: int
    reference_state: str


@dataclass(frozen=True, slots=True)
class ArtifactInspectionRecord:
    """Stable descriptor, graph classification, and logical references."""

    schema_version: str
    artifact_id: ArtifactID
    integrity_status: str
    schema_id: str | None
    media_type: str | None
    size_bytes: int | None
    payload_sha256: str | None
    descriptor_sha256: str | None
    producer: str | None
    dependency_artifact_ids: tuple[ArtifactID, ...]
    classifications: tuple[str, ...]
    references: tuple[ArtifactReferenceView, ...]


@dataclass(frozen=True, slots=True)
class ArtifactVerificationRecord:
    """Content verification result for one immutable artifact identity."""

    schema_version: str
    artifact_id: ArtifactID
    valid: bool
    payload_sha256: str | None
    descriptor_sha256: str | None
    size_bytes: int | None
    failure: str | None


@dataclass(frozen=True, slots=True)
class LogicalArtifactResolution:
    """Exact resolution of a logical revision to verified immutable content."""

    schema_version: str
    reference: ArtifactReferenceView
    target: ArtifactVerificationRecord


@dataclass(frozen=True, slots=True)
class ArtifactInspectionPage:
    """One bounded immutable artifact inventory page."""

    schema_version: str
    artifacts: tuple[ArtifactInspectionRecord, ...]
    page: dict[str, object]


class RuntimeArtifactInspector:
    """List, resolve, and verify artifacts under a shared snapshot lease."""

    def __init__(
        self,
        *,
        database_path: Path,
        payload_store: AtomicFilesystemArtifactPayloadStore,
        lock_timeout_seconds: float = 5.0,
        max_inventory_artifacts: int = 100_000,
    ) -> None:
        if max_inventory_artifacts < 1:
            raise ValueError("artifact inventory limit must be positive")
        self._database_path = database_path
        self._payload_store = payload_store
        self._lock_timeout_seconds = lock_timeout_seconds
        self._max_inventory_artifacts = max_inventory_artifacts

    def list_artifacts(self) -> tuple[ArtifactInspectionRecord, ...]:
        """Return a small complete inventory or require explicit pagination."""
        page = self.list_artifacts_page(PageRequest(limit=1000))
        if page.page["next_cursor"] is not None:
            raise ValueError("complete artifact listing exceeds 1000; use pagination")
        return page.artifacts

    def list_artifacts_page(self, page: PageRequest) -> ArtifactInspectionPage:
        """Return one stable, bounded page of stored and referenced artifacts."""
        store = self._read_store()
        try:
            report = ArtifactReachabilityValidator(
                database_path=self._database_path,
                payload_store=self._payload_store,
                lock_timeout_seconds=self._lock_timeout_seconds,
                max_artifacts=self._max_inventory_artifacts,
            ).validate()
            reference_map = self._references(
                store._connection,
                max_references=self._max_inventory_artifacts,
            )
            identities: set[ArtifactID] = set()
            for index, artifact_id in enumerate(
                self._payload_store.iter_artifact_ids(), start=1
            ):
                if index > self._max_inventory_artifacts:
                    raise ValueError("artifact inventory exceeds its configured limit")
                identities.add(artifact_id)
            identities.update(report.missing_artifact_ids)
            identities.update(report.orphan_artifact_ids)
            identities.update(report.reachable_artifact_ids)
            identities.update(report.superseded_artifact_ids)
            ordered = tuple(sorted(identities))
            if len(ordered) > self._max_inventory_artifacts:
                raise ValueError("artifact inventory exceeds its configured limit")
            pagination = paginate_collections(
                {"artifacts": ordered},
                collection_fields=("artifacts",),
                resource_identity={"report_sha256": report.report_sha256},
                request=page,
            )
            metadata = pagination["page"]
            assert isinstance(metadata, dict)
            offset = metadata["offset"]
            assert isinstance(offset, int)
            selected = ordered[offset : offset + page.limit]
            records = tuple(
                self._inspection_record(
                    artifact_id,
                    report=report,
                    references=reference_map.get(artifact_id, ()),
                )
                for artifact_id in selected
            )
            return ArtifactInspectionPage(
                schema_version="bijux.runtime.artifact-inspection-page.v1",
                artifacts=records,
                page=metadata,
            )
        finally:
            store.close()

    def resolve(
        self,
        *,
        tenant_id: TenantID,
        run_id: RunID,
        logical_artifact_id: str,
        revision: int | None = None,
    ) -> LogicalArtifactResolution:
        """Resolve the active or requested immutable logical-reference revision."""
        if not logical_artifact_id.strip() or revision is not None and revision < 0:
            raise ValueError("logical artifact identity and revision are invalid")
        store = self._read_store()
        try:
            parameters: tuple[object, ...] = (
                str(tenant_id),
                str(run_id),
                logical_artifact_id,
            )
            revision_clause = "AND reference_state = 'active'"
            if revision is not None:
                revision_clause = "AND revision = ?"
                parameters = (*parameters, revision)
            rows = store._connection.execute(
                f"""
                SELECT revision, target_artifact_id, reference_state
                FROM artifact_references
                WHERE tenant_id = ? AND run_id = ? AND logical_artifact_id = ?
                  {revision_clause}
                ORDER BY revision
                """,
                parameters,
            ).fetchall()
            if not rows:
                raise KeyError(
                    f"logical artifact reference not found: {logical_artifact_id}"
                )
            if len(rows) != 1:
                raise ValueError(
                    "logical artifact reference has split-brain activation"
                )
            resolved_revision, target_id, state = rows[0]
            reference = ArtifactReferenceView(
                tenant_id=tenant_id,
                run_id=run_id,
                logical_artifact_id=logical_artifact_id,
                revision=int(resolved_revision),
                reference_state=state,
            )
            return LogicalArtifactResolution(
                schema_version="bijux.runtime.logical-artifact-resolution.v1",
                reference=reference,
                target=self.verify(ArtifactID(target_id)),
            )
        finally:
            store.close()

    def verify(self, artifact_id: ArtifactID) -> ArtifactVerificationRecord:
        """Verify descriptor, payload checksum, size, and content identity."""
        try:
            artifact = self._payload_store.load(artifact_id)
        except (KeyError, PayloadCorruptionError, ValueError) as exc:
            return ArtifactVerificationRecord(
                schema_version="bijux.runtime.artifact-verification.v1",
                artifact_id=artifact_id,
                valid=False,
                payload_sha256=None,
                descriptor_sha256=None,
                size_bytes=None,
                failure=type(exc).__name__,
            )
        descriptor_bytes = canonical_json_bytes(
            self._descriptor_record(artifact.descriptor)
        )
        return ArtifactVerificationRecord(
            schema_version="bijux.runtime.artifact-verification.v1",
            artifact_id=artifact_id,
            valid=True,
            payload_sha256=str(artifact.descriptor.payload_sha256),
            descriptor_sha256=hashlib.sha256(descriptor_bytes).hexdigest(),
            size_bytes=artifact.descriptor.size_bytes,
            failure=None,
        )

    def _read_store(self) -> DuckDBExecutionStore:
        return DuckDBExecutionStore(
            self._database_path,
            read_only=True,
            lock_timeout_seconds=self._lock_timeout_seconds,
        )

    def _inspection_record(
        self,
        artifact_id: ArtifactID,
        *,
        report: ArtifactReachabilityReport,
        references: tuple[ArtifactReferenceView, ...],
    ) -> ArtifactInspectionRecord:
        classifications = tuple(
            name
            for name, identities in (
                ("root", report.root_artifact_ids),
                ("reachable", report.reachable_artifact_ids),
                ("orphan", report.orphan_artifact_ids),
                ("missing", report.missing_artifact_ids),
                ("corrupt", report.corrupt_artifact_ids),
                ("superseded", report.superseded_artifact_ids),
            )
            if artifact_id in identities
        )
        try:
            artifact = self._payload_store.load(artifact_id)
        except (KeyError, PayloadCorruptionError, ValueError):
            return ArtifactInspectionRecord(
                "bijux.runtime.artifact-inspection.v1",
                artifact_id,
                "missing" if artifact_id in report.missing_artifact_ids else "corrupt",
                None,
                None,
                None,
                None,
                None,
                None,
                (),
                classifications,
                references,
            )
        descriptor = artifact.descriptor
        descriptor_hash = hashlib.sha256(
            canonical_json_bytes(self._descriptor_record(descriptor))
        ).hexdigest()
        return ArtifactInspectionRecord(
            "bijux.runtime.artifact-inspection.v1",
            artifact_id,
            "valid",
            descriptor.schema_id,
            descriptor.media_type,
            descriptor.size_bytes,
            str(descriptor.payload_sha256),
            descriptor_hash,
            descriptor.producer,
            descriptor.dependencies,
            classifications,
            references,
        )

    @staticmethod
    def _references(
        connection: duckdb.DuckDBPyConnection,
        *,
        max_references: int,
    ) -> dict[ArtifactID, tuple[ArtifactReferenceView, ...]]:
        grouped: dict[ArtifactID, list[ArtifactReferenceView]] = {}
        rows = connection.execute(
            """
            SELECT tenant_id, run_id, logical_artifact_id, revision,
                   target_artifact_id, reference_state
            FROM artifact_references
            ORDER BY tenant_id, run_id, logical_artifact_id, revision
            LIMIT ?
            """,
            [max_references + 1],
        ).fetchall()
        if len(rows) > max_references:
            raise ValueError("artifact references exceed their configured limit")
        for tenant_id, run_id, logical_id, revision, target_id, state in rows:
            grouped.setdefault(ArtifactID(target_id), []).append(
                ArtifactReferenceView(
                    TenantID(tenant_id),
                    RunID(run_id),
                    logical_id,
                    int(revision),
                    state,
                )
            )
        return {key: tuple(value) for key, value in grouped.items()}

    @staticmethod
    def _descriptor_record(
        descriptor: ImmutableArtifactDescriptor,
    ) -> dict[str, object]:
        return {
            "artifact_id": str(descriptor.artifact_id),
            "dependencies": [str(item) for item in descriptor.dependencies],
            "media_type": descriptor.media_type,
            "payload_sha256": str(descriptor.payload_sha256),
            "producer": descriptor.producer,
            "schema_id": descriptor.schema_id,
            "size_bytes": descriptor.size_bytes,
        }


__all__ = [
    "ArtifactInspectionRecord",
    "ArtifactInspectionPage",
    "ArtifactReferenceView",
    "ArtifactVerificationRecord",
    "LogicalArtifactResolution",
    "RuntimeArtifactInspector",
]
