# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Report-only reachability and integrity validation for Runtime artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

import duckdb

from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionStore,
)
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.persistence.filesystem_payload_store import (
    AtomicFilesystemArtifactPayloadStore,
    PayloadCorruptionError,
)


@dataclass(frozen=True, slots=True)
class ArtifactReachabilityReport:
    """Deterministic classification of the complete artifact inventory."""

    schema_version: str
    root_artifact_ids: tuple[ArtifactID, ...]
    reachable_artifact_ids: tuple[ArtifactID, ...]
    orphan_artifact_ids: tuple[ArtifactID, ...]
    missing_artifact_ids: tuple[ArtifactID, ...]
    corrupt_artifact_ids: tuple[ArtifactID, ...]
    superseded_artifact_ids: tuple[ArtifactID, ...]
    report_sha256: str

    @property
    def integrity_ok(self) -> bool:
        """Return whether all reachable content is present and valid."""
        return not self.missing_artifact_ids and not self.corrupt_artifact_ids


class ArtifactReachabilityValidator:
    """Traverse admitted metadata roots without modifying database or blobs."""

    _REQUIRED_TABLES = {
        "artifact_payload_dependencies",
        "artifact_payloads",
        "artifact_references",
        "publication_transaction_artifacts",
        "publication_transactions",
        "run_attempts",
        "run_checks",
        "run_dags",
        "run_policies",
        "run_publications",
        "run_revisions",
        "runtime_jobs",
    }

    def __init__(
        self,
        *,
        database_path: Path,
        payload_store: AtomicFilesystemArtifactPayloadStore,
        lock_timeout_seconds: float = 5.0,
        max_artifacts: int = 100_000,
        max_dependency_edges: int = 1_000_000,
    ) -> None:
        if max_artifacts < 1 or max_dependency_edges < 1:
            raise ValueError("artifact reachability limits must be positive")
        self._database_path = database_path
        self._payload_store = payload_store
        self._lock_timeout_seconds = lock_timeout_seconds
        self._max_artifacts = max_artifacts
        self._max_dependency_edges = max_dependency_edges

    def validate(self) -> ArtifactReachabilityReport:
        """Verify the whole graph and return stable, non-destructive findings."""
        store = DuckDBExecutionStore(
            self._database_path,
            read_only=True,
            lock_timeout_seconds=self._lock_timeout_seconds,
        )
        connection = store._connection
        try:
            tables = {
                row[0]
                for row in connection.execute(
                    """
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'main'
                    """
                ).fetchall()
            }
            missing_tables = self._REQUIRED_TABLES - tables
            if missing_tables:
                raise ValueError(
                    "metadata schema is missing required tables: "
                    + ", ".join(sorted(missing_tables))
                )
            roots = self._root_ids(connection, limit=self._max_artifacts)
            dependencies = self._dependencies(
                connection,
                limit=self._max_dependency_edges,
            )
            metadata_ids = {
                ArtifactID(row[0])
                for row in self._bounded_rows(
                    connection,
                    "SELECT artifact_id FROM artifact_payloads",
                    limit=self._max_artifacts,
                    collection="artifact metadata",
                )
            }
            superseded_targets = {
                ArtifactID(row[0])
                for row in self._bounded_rows(
                    connection,
                    """
                    SELECT DISTINCT target_artifact_id FROM artifact_references
                    WHERE reference_state = 'superseded'
                    """,
                    limit=self._max_artifacts,
                    collection="superseded artifacts",
                )
            }
        finally:
            store.close()

        reachable = self._transitive_closure(
            roots,
            dependencies,
            limit=self._max_artifacts,
        )
        stored: set[ArtifactID] = set()
        for artifact_id in self._payload_store.iter_artifact_ids():
            if len(stored) >= self._max_artifacts:
                raise ValueError("stored artifact inventory exceeds its limit")
            stored.add(artifact_id)
        missing = reachable - stored
        corrupt = {
            artifact_id for artifact_id in stored if self._is_corrupt(artifact_id)
        }
        valid_stored = stored - corrupt
        superseded = (superseded_targets - reachable) & valid_stored
        orphan = valid_stored - reachable - superseded
        # Metadata with no admitted path is also orphaned even if its blob is absent.
        orphan |= (metadata_ids - reachable - superseded_targets) - missing
        schema_version = "bijux.runtime.reachability.v1"
        root_ids = tuple(sorted(roots))
        reachable_ids = tuple(sorted(reachable))
        orphan_ids = tuple(sorted(orphan))
        missing_ids = tuple(sorted(missing))
        corrupt_ids = tuple(sorted(corrupt))
        superseded_ids = tuple(sorted(superseded))
        report_fields: dict[str, object] = {
            "schema_version": schema_version,
            "root_artifact_ids": [str(item) for item in root_ids],
            "reachable_artifact_ids": [str(item) for item in reachable_ids],
            "orphan_artifact_ids": [str(item) for item in orphan_ids],
            "missing_artifact_ids": [str(item) for item in missing_ids],
            "corrupt_artifact_ids": [str(item) for item in corrupt_ids],
            "superseded_artifact_ids": [str(item) for item in superseded_ids],
        }
        report_hash = hashlib.sha256(
            json.dumps(
                report_fields,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return ArtifactReachabilityReport(
            schema_version=schema_version,
            root_artifact_ids=root_ids,
            reachable_artifact_ids=reachable_ids,
            orphan_artifact_ids=orphan_ids,
            missing_artifact_ids=missing_ids,
            corrupt_artifact_ids=corrupt_ids,
            superseded_artifact_ids=superseded_ids,
            report_sha256=report_hash,
        )

    @staticmethod
    def canonical_report_bytes(report: ArtifactReachabilityReport) -> bytes:
        """Serialize a report for durable evidence without filesystem paths."""
        record = asdict(report)
        return json.dumps(
            record,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    @staticmethod
    def _root_ids(
        connection: duckdb.DuckDBPyConnection,
        *,
        limit: int,
    ) -> set[ArtifactID]:
        queries = (
            (
                "SELECT artifact_id FROM artifact_payloads WHERE schema_id IN "
                "('bijux.runtime.execution-manifest.v1', "
                "'bijux.runtime.execution-event.v1')"
            ),
            "SELECT target_artifact_id FROM artifact_references WHERE reference_state = 'active'",
            "SELECT payload_artifact_id FROM run_revisions",
            "SELECT payload_artifact_id FROM run_dags",
            "SELECT payload_artifact_id FROM run_policies",
            "SELECT evidence_artifact_id FROM run_checks",
            "SELECT failure_artifact_id FROM run_attempts WHERE failure_artifact_id IS NOT NULL",
            "SELECT manifest_artifact_id FROM run_publications WHERE publication_state = 'admitted'",
            "SELECT receipt_artifact_id FROM run_publications WHERE publication_state = 'admitted'",
            "SELECT request_artifact_id FROM runtime_jobs",
            "SELECT result_artifact_id FROM runtime_jobs WHERE result_artifact_id IS NOT NULL",
        )
        roots: set[ArtifactID] = set()
        for query in queries:
            cursor = connection.execute(query)
            while rows := cursor.fetchmany(1000):
                roots.update(ArtifactID(row[0]) for row in rows)
                if len(roots) > limit:
                    raise ValueError("artifact reachability roots exceed their limit")
        return roots

    @staticmethod
    def _dependencies(
        connection: duckdb.DuckDBPyConnection,
        *,
        limit: int,
    ) -> dict[ArtifactID, set[ArtifactID]]:
        graph: dict[ArtifactID, set[ArtifactID]] = {}
        cursor = connection.execute(
            """
            SELECT artifact_id, dependency_artifact_id
            FROM artifact_payload_dependencies
            """
        )
        edge_count = 0
        while rows := cursor.fetchmany(1000):
            edge_count += len(rows)
            if edge_count > limit:
                raise ValueError("artifact dependency graph exceeds its edge limit")
            for artifact_id, dependency_id in rows:
                graph.setdefault(ArtifactID(artifact_id), set()).add(
                    ArtifactID(dependency_id)
                )
        return graph

    @staticmethod
    def _transitive_closure(
        roots: set[ArtifactID],
        dependencies: dict[ArtifactID, set[ArtifactID]],
        *,
        limit: int,
    ) -> set[ArtifactID]:
        reachable: set[ArtifactID] = set()
        pending = list(roots)
        while pending:
            current = pending.pop()
            if current in reachable:
                continue
            if len(reachable) >= limit:
                raise ValueError("reachable artifact closure exceeds its limit")
            reachable.add(current)
            pending.extend(dependencies.get(current, ()))
        return reachable

    @staticmethod
    def _bounded_rows(
        connection: duckdb.DuckDBPyConnection,
        query: str,
        *,
        limit: int,
        collection: str,
    ) -> list[tuple[object, ...]]:
        rows = connection.execute(f"{query} LIMIT ?", [limit + 1]).fetchall()
        if len(rows) > limit:
            raise ValueError(f"{collection} exceed their configured limit")
        return rows

    def _is_corrupt(self, artifact_id: ArtifactID) -> bool:
        try:
            self._payload_store.load(artifact_id)
        except (KeyError, PayloadCorruptionError, ValueError):
            return True
        return False


__all__ = [
    "ArtifactReachabilityReport",
    "ArtifactReachabilityValidator",
]
