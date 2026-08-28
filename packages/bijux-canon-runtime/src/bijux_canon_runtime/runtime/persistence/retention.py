# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Checksummed retention planning and recoverable garbage collection."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path

import duckdb

from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionStore,
)
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.persistence.filesystem_payload_store import (
    AtomicFilesystemArtifactPayloadStore,
)
from bijux_canon_runtime.runtime.persistence.reachability import (
    ArtifactReachabilityReport,
    ArtifactReachabilityValidator,
)


class GarbageCollectionSafetyError(RuntimeError):
    """Raised when retention or recovery safety cannot be proven."""


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    """Explicit eligibility policy; history is preserved by default."""

    collect_orphans: bool = True
    collect_superseded: bool = False
    held_artifact_ids: tuple[ArtifactID, ...] = ()


@dataclass(frozen=True, slots=True)
class GarbageCollectionCandidate:
    """One classified artifact and its planned disposition."""

    artifact_id: ArtifactID
    classification: str
    disposition: str
    reason: str


@dataclass(frozen=True, slots=True)
class GarbageCollectionPlan:
    """Immutable, checksummed collection intent."""

    schema_version: str
    plan_id: str
    reachability_sha256: str
    policy_json: str
    candidates: tuple[GarbageCollectionCandidate, ...]
    created_at: str
    plan_sha256: str

    @property
    def eligible_artifact_ids(self) -> tuple[ArtifactID, ...]:
        return tuple(
            item.artifact_id
            for item in self.candidates
            if item.disposition == "eligible"
        )


@dataclass(frozen=True, slots=True)
class GarbageCollectionResult:
    """Durable collection state with exact recovery coverage."""

    plan_id: str
    status: str
    applied_artifact_ids: tuple[ArtifactID, ...]
    backup_root: str


class SafeGarbageCollector:
    """Apply only confirmed plans while retaining backup and quarantine copies."""

    def __init__(
        self,
        *,
        database_path: Path,
        payload_store: AtomicFilesystemArtifactPayloadStore,
    ) -> None:
        self._database_path = database_path
        self._payload_store = payload_store

    def add_hold(
        self,
        *,
        hold_id: str,
        artifact_id: ArtifactID,
        reason: str,
        created_at: str,
    ) -> None:
        """Persist an idempotent hold independently of one plan."""
        if not hold_id.strip() or not reason.strip():
            raise ValueError("hold identity and reason must not be empty")
        store = DuckDBExecutionStore(self._database_path)
        try:
            existing = store._connection.execute(
                """
                SELECT reason, created_at, released_at FROM artifact_holds
                WHERE hold_id = ? AND artifact_id = ?
                """,
                (hold_id, str(artifact_id)),
            ).fetchone()
            expected = (reason, created_at, None)
            if existing is not None and tuple(existing) != expected:
                raise GarbageCollectionSafetyError(
                    "hold identity has conflicting state"
                )
            if existing is None:
                store._connection.execute(
                    """
                    INSERT INTO artifact_holds (
                        hold_id, artifact_id, reason, created_at, released_at
                    ) VALUES (?, ?, ?, ?, NULL)
                    """,
                    (hold_id, str(artifact_id), reason, created_at),
                )
        finally:
            store.close()

    def plan(
        self,
        *,
        plan_id: str,
        report: ArtifactReachabilityReport,
        policy: RetentionPolicy,
        created_at: str,
    ) -> GarbageCollectionPlan:
        """Persist and return a checksummed report-derived plan."""
        if not plan_id.strip() or not report.integrity_ok:
            raise GarbageCollectionSafetyError(
                "collection requires a named, integrity-clean reachability report"
            )
        store = DuckDBExecutionStore(self._database_path)
        try:
            current = ArtifactReachabilityValidator(
                database_path=self._database_path,
                payload_store=self._payload_store,
            ).validate()
            if current.report_sha256 != report.report_sha256:
                raise GarbageCollectionSafetyError(
                    "reachability changed before collection planning"
                )
            held = set(policy.held_artifact_ids)
            held.update(
                ArtifactID(row[0])
                for row in store._connection.execute(
                    "SELECT artifact_id FROM artifact_holds WHERE released_at IS NULL"
                ).fetchall()
            )
            candidates: list[GarbageCollectionCandidate] = []
            for classification, identities, enabled in (
                ("orphan", report.orphan_artifact_ids, policy.collect_orphans),
                (
                    "superseded",
                    report.superseded_artifact_ids,
                    policy.collect_superseded,
                ),
            ):
                for artifact_id in identities:
                    is_held = artifact_id in held or not enabled
                    candidates.append(
                        GarbageCollectionCandidate(
                            artifact_id=artifact_id,
                            classification=classification,
                            disposition="held" if is_held else "eligible",
                            reason=(
                                "active hold or retention policy"
                                if is_held
                                else f"collect {classification} artifact"
                            ),
                        )
                    )
            candidates.sort(key=lambda item: str(item.artifact_id))
            policy_json = json.dumps(
                {
                    "collect_orphans": policy.collect_orphans,
                    "collect_superseded": policy.collect_superseded,
                    "held_artifact_ids": sorted(str(item) for item in held),
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            schema_version = "bijux.runtime.garbage-collection-plan.v1"
            unsigned: dict[str, object] = {
                "candidates": [
                    {
                        "artifact_id": str(item.artifact_id),
                        "classification": item.classification,
                        "disposition": item.disposition,
                        "reason": item.reason,
                    }
                    for item in candidates
                ],
                "created_at": created_at,
                "plan_id": plan_id,
                "policy_json": policy_json,
                "reachability_sha256": report.report_sha256,
                "schema_version": schema_version,
            }
            plan_hash = hashlib.sha256(
                json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode(
                    "utf-8"
                )
            ).hexdigest()
            plan = GarbageCollectionPlan(
                schema_version=schema_version,
                plan_id=plan_id,
                reachability_sha256=report.report_sha256,
                policy_json=policy_json,
                candidates=tuple(candidates),
                created_at=created_at,
                plan_sha256=plan_hash,
            )
            self._persist_plan(store._connection, plan)
            return plan
        finally:
            store.close()

    def apply(
        self,
        plan: GarbageCollectionPlan,
        *,
        confirmation: str,
        backup_root: Path,
        applied_at: str,
    ) -> GarbageCollectionResult:
        """Apply only an exact confirmed plan after durable backup verification."""
        self._assert_plan_hash(plan)
        if confirmation != f"apply:{plan.plan_sha256}":
            raise GarbageCollectionSafetyError("collection confirmation is invalid")
        backup_path = backup_root.resolve()
        if (
            backup_path == self._payload_store.root
            or self._payload_store.root in backup_path.parents
        ):
            raise GarbageCollectionSafetyError(
                "backup root must be outside the active CAS"
            )
        store = DuckDBExecutionStore(self._database_path)
        try:
            current = ArtifactReachabilityValidator(
                database_path=self._database_path,
                payload_store=self._payload_store,
            ).validate()
            if current.report_sha256 != plan.reachability_sha256:
                raise GarbageCollectionSafetyError(
                    "reachability changed after collection planning"
                )
            active_holds = {
                ArtifactID(row[0])
                for row in store._connection.execute(
                    "SELECT artifact_id FROM artifact_holds WHERE released_at IS NULL"
                ).fetchall()
            }
            if active_holds.intersection(plan.eligible_artifact_ids):
                raise GarbageCollectionSafetyError(
                    "collection candidate acquired an active hold"
                )
            backup = AtomicFilesystemArtifactPayloadStore(backup_path)
            moved: list[tuple[Path, Path]] = []
            try:
                for artifact_id in plan.eligible_artifact_ids:
                    source = self._payload_store.artifact_directory(artifact_id)
                    digest = str(artifact_id).removeprefix("sha256:")
                    quarantine = (
                        self._payload_store.root
                        / "quarantine"
                        / plan.plan_id
                        / digest[:2]
                        / digest
                    )
                    if not source.exists() and quarantine.exists():
                        backup.load(artifact_id)
                        moved.append((source, quarantine))
                        continue
                    if not source.exists() or quarantine.exists():
                        raise GarbageCollectionSafetyError(
                            "collection candidate has ambiguous active state"
                        )
                    artifact = self._payload_store.load(artifact_id)
                    backup.put(artifact)
                    if backup.load(artifact_id) != artifact:
                        raise GarbageCollectionSafetyError("backup verification failed")
                    quarantine.parent.mkdir(parents=True, exist_ok=True)
                    os.rename(source, quarantine)
                    moved.append((source, quarantine))
            except Exception:
                for source, quarantine in reversed(moved):
                    source.parent.mkdir(parents=True, exist_ok=True)
                    os.rename(quarantine, source)
                raise
            self._set_status(
                plan,
                expected="planned",
                status="applied",
                timestamp_column="applied_at",
                timestamp=applied_at,
                backup_root=str(backup_path),
            )
        finally:
            store.close()
        return GarbageCollectionResult(
            plan_id=plan.plan_id,
            status="applied",
            applied_artifact_ids=plan.eligible_artifact_ids,
            backup_root=str(backup_path),
        )

    def verify(
        self,
        plan: GarbageCollectionPlan,
        *,
        backup_root: Path,
        verified_at: str,
    ) -> GarbageCollectionResult:
        """Verify active removal and exact backup coverage for every candidate."""
        self._assert_plan_hash(plan)
        backup = AtomicFilesystemArtifactPayloadStore(backup_root)
        for artifact_id in plan.eligible_artifact_ids:
            if self._payload_store.artifact_directory(artifact_id).exists():
                raise GarbageCollectionSafetyError("collected artifact remains active")
            backup.load(artifact_id)
        self._set_status(
            plan,
            expected="applied",
            status="verified",
            timestamp_column="verified_at",
            timestamp=verified_at,
            backup_root=str(backup_root.resolve()),
        )
        return GarbageCollectionResult(
            plan.plan_id,
            "verified",
            plan.eligible_artifact_ids,
            str(backup_root.resolve()),
        )

    def rollback(
        self,
        plan: GarbageCollectionPlan,
        *,
        backup_root: Path,
        rolled_back_at: str,
    ) -> GarbageCollectionResult:
        """Restore every collected object from its verified backup."""
        backup = AtomicFilesystemArtifactPayloadStore(backup_root)
        for artifact_id in plan.eligible_artifact_ids:
            artifact = backup.load(artifact_id)
            self._payload_store.put(artifact)
            if self._payload_store.load(artifact_id) != artifact:
                raise GarbageCollectionSafetyError("rollback verification failed")
        self._set_status(
            plan,
            expected="verified",
            status="rolled_back",
            timestamp_column="rolled_back_at",
            timestamp=rolled_back_at,
            backup_root=str(backup_root.resolve()),
        )
        return GarbageCollectionResult(
            plan.plan_id,
            "rolled_back",
            plan.eligible_artifact_ids,
            str(backup_root.resolve()),
        )

    @staticmethod
    def _assert_plan_hash(plan: GarbageCollectionPlan) -> None:
        unsigned = {
            "candidates": [
                {
                    "artifact_id": str(item.artifact_id),
                    "classification": item.classification,
                    "disposition": item.disposition,
                    "reason": item.reason,
                }
                for item in plan.candidates
            ],
            "created_at": plan.created_at,
            "plan_id": plan.plan_id,
            "policy_json": plan.policy_json,
            "reachability_sha256": plan.reachability_sha256,
            "schema_version": plan.schema_version,
        }
        actual = hashlib.sha256(
            json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if actual != plan.plan_sha256:
            raise GarbageCollectionSafetyError("collection plan checksum is invalid")

    @staticmethod
    def _persist_plan(
        connection: duckdb.DuckDBPyConnection,
        plan: GarbageCollectionPlan,
    ) -> None:
        existing = connection.execute(
            "SELECT plan_sha256 FROM garbage_collection_plans WHERE plan_id = ?",
            (plan.plan_id,),
        ).fetchone()
        if existing is not None:
            if existing[0] != plan.plan_sha256:
                raise GarbageCollectionSafetyError("plan identity has conflicting hash")
            return
        connection.execute("BEGIN")
        try:
            connection.execute(
                """
                INSERT INTO garbage_collection_plans (
                    plan_id, plan_sha256, reachability_sha256, policy_json,
                    status, created_at
                ) VALUES (?, ?, ?, ?, 'planned', ?)
                """,
                (
                    plan.plan_id,
                    plan.plan_sha256,
                    plan.reachability_sha256,
                    plan.policy_json,
                    plan.created_at,
                ),
            )
            for item in plan.candidates:
                connection.execute(
                    """
                    INSERT INTO garbage_collection_candidates (
                        plan_id, artifact_id, classification, disposition, reason
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        plan.plan_id,
                        str(item.artifact_id),
                        item.classification,
                        item.disposition,
                        item.reason,
                    ),
                )
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise

    def _set_status(
        self,
        plan: GarbageCollectionPlan,
        *,
        expected: str,
        status: str,
        timestamp_column: str,
        timestamp: str,
        backup_root: str,
    ) -> None:
        store = DuckDBExecutionStore(self._database_path)
        try:
            row = store._connection.execute(
                "SELECT plan_sha256, status FROM garbage_collection_plans WHERE plan_id = ?",
                (plan.plan_id,),
            ).fetchone()
            if row != (plan.plan_sha256, expected):
                raise GarbageCollectionSafetyError(
                    "collection history does not permit this transition"
                )
            store._connection.execute(
                f"""
                UPDATE garbage_collection_plans
                SET status = ?, {timestamp_column} = ?, backup_root = ?
                WHERE plan_id = ? AND status = ?
                """,
                (status, timestamp, backup_root, plan.plan_id, expected),
            )
        finally:
            store.close()


__all__ = [
    "GarbageCollectionCandidate",
    "GarbageCollectionPlan",
    "GarbageCollectionResult",
    "GarbageCollectionSafetyError",
    "RetentionPolicy",
    "SafeGarbageCollector",
]
