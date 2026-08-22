# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Report-only reachability and integrity validation for Runtime artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

import duckdb

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
    }

    def __init__(
        self,
        *,
        database_path: Path,
        payload_store: AtomicFilesystemArtifactPayloadStore,
    ) -> None:
        self._database_path = database_path
        self._payload_store = payload_store

    def validate(self) -> ArtifactReachabilityReport:
        """Verify the whole graph and return stable, non-destructive findings."""
        connection = duckdb.connect(str(self._database_path), read_only=True)
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
            roots = self._root_ids(connection)
            dependencies = self._dependencies(connection)
            metadata_ids = {
                ArtifactID(row[0])
                for row in connection.execute(
                    "SELECT artifact_id FROM artifact_payloads"
                ).fetchall()
            }
            superseded_targets = {
                ArtifactID(row[0])
                for row in connection.execute(
                    """
                    SELECT DISTINCT target_artifact_id FROM artifact_references
                    WHERE reference_state = 'superseded'
                    """
                ).fetchall()
            }
        finally:
            connection.close()

        reachable = self._transitive_closure(roots, dependencies)
        stored = set(self._payload_store.artifact_ids())
        missing = reachable - stored
        corrupt = {
            artifact_id for artifact_id in stored if self._is_corrupt(artifact_id)
        }
        valid_stored = stored - corrupt
        superseded = (superseded_targets - reachable) & valid_stored
        orphan = valid_stored - reachable - superseded
        # Metadata with no admitted path is also orphaned even if its blob is absent.
        orphan |= (metadata_ids - reachable - superseded_targets) - missing
        report_fields = {
            "schema_version": "bijux.runtime.reachability.v1",
            "root_artifact_ids": sorted(str(item) for item in roots),
            "reachable_artifact_ids": sorted(str(item) for item in reachable),
            "orphan_artifact_ids": sorted(str(item) for item in orphan),
            "missing_artifact_ids": sorted(str(item) for item in missing),
            "corrupt_artifact_ids": sorted(str(item) for item in corrupt),
            "superseded_artifact_ids": sorted(str(item) for item in superseded),
        }
        report_hash = hashlib.sha256(
            json.dumps(
                report_fields,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return ArtifactReachabilityReport(
            schema_version=report_fields["schema_version"],
            root_artifact_ids=tuple(
                ArtifactID(item) for item in report_fields["root_artifact_ids"]
            ),
            reachable_artifact_ids=tuple(
                ArtifactID(item) for item in report_fields["reachable_artifact_ids"]
            ),
            orphan_artifact_ids=tuple(
                ArtifactID(item) for item in report_fields["orphan_artifact_ids"]
            ),
            missing_artifact_ids=tuple(
                ArtifactID(item) for item in report_fields["missing_artifact_ids"]
            ),
            corrupt_artifact_ids=tuple(
                ArtifactID(item) for item in report_fields["corrupt_artifact_ids"]
            ),
            superseded_artifact_ids=tuple(
                ArtifactID(item) for item in report_fields["superseded_artifact_ids"]
            ),
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
    def _root_ids(connection: duckdb.DuckDBPyConnection) -> set[ArtifactID]:
        queries = (
            "SELECT target_artifact_id FROM artifact_references WHERE reference_state = 'active'",
            "SELECT payload_artifact_id FROM run_revisions",
            "SELECT payload_artifact_id FROM run_dags",
            "SELECT payload_artifact_id FROM run_policies",
            "SELECT evidence_artifact_id FROM run_checks",
            "SELECT failure_artifact_id FROM run_attempts WHERE failure_artifact_id IS NOT NULL",
            "SELECT manifest_artifact_id FROM run_publications WHERE publication_state = 'admitted'",
            "SELECT receipt_artifact_id FROM run_publications WHERE publication_state = 'admitted'",
        )
        roots: set[ArtifactID] = set()
        for query in queries:
            roots.update(
                ArtifactID(row[0]) for row in connection.execute(query).fetchall()
            )
        return roots

    @staticmethod
    def _dependencies(
        connection: duckdb.DuckDBPyConnection,
    ) -> dict[ArtifactID, set[ArtifactID]]:
        graph: dict[ArtifactID, set[ArtifactID]] = {}
        for artifact_id, dependency_id in connection.execute(
            """
            SELECT artifact_id, dependency_artifact_id
            FROM artifact_payload_dependencies
            """
        ).fetchall():
            graph.setdefault(ArtifactID(artifact_id), set()).add(
                ArtifactID(dependency_id)
            )
        return graph

    @staticmethod
    def _transitive_closure(
        roots: set[ArtifactID],
        dependencies: dict[ArtifactID, set[ArtifactID]],
    ) -> set[ArtifactID]:
        reachable: set[ArtifactID] = set()
        pending = list(roots)
        while pending:
            current = pending.pop()
            if current in reachable:
                continue
            reachable.add(current)
            pending.extend(dependencies.get(current, ()))
        return reachable

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
