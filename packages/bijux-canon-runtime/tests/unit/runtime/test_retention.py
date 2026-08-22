from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import duckdb
import pytest

from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.model.execution.run_mode import RunMode
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionWriteStore,
)
from bijux_canon_runtime.runtime.persistence import (
    ArtifactPublicationCoordinator,
    ArtifactReachabilityValidator,
    AtomicFilesystemArtifactPayloadStore,
    GarbageCollectionSafetyError,
    PublicationItem,
    RetentionPolicy,
    SafeGarbageCollector,
)


_NOW = "2026-08-22T00:00:00+00:00"


def _workspace(tmp_path: Path, resolved_flow):
    db_path = tmp_path / "runtime.duckdb"
    execution = DuckDBExecutionWriteStore(db_path)
    run_id = execution.save_run(
        trace=None,
        plan=resolved_flow.plan,
        mode=RunMode.DRY_RUN,
    )
    execution._store.close()
    store = AtomicFilesystemArtifactPayloadStore(tmp_path / "cas")
    coordinator = ArtifactPublicationCoordinator(
        payload_store=store,
        database_path=db_path,
    )
    tenant_id = resolved_flow.manifest.tenant_id
    first = AddressedArtifact.from_json(
        {"value": "first"},
        schema_id="bijux.runtime.result.v1",
        producer="bijux-canon-runtime:research",
    )
    active = AddressedArtifact.from_json(
        {"value": "active"},
        schema_id="bijux.runtime.result.v1",
        producer="bijux-canon-runtime:research",
    )
    coordinator.publish(
        tenant_id=tenant_id,
        run_id=run_id,
        transaction_id="publish-0",
        items=(PublicationItem("result/current", 0, first),),
        created_at=_NOW,
        completed_at=_NOW,
    )
    coordinator.publish(
        tenant_id=tenant_id,
        run_id=run_id,
        transaction_id="publish-1",
        items=(PublicationItem("result/current", 1, active),),
        created_at=_NOW,
        completed_at=_NOW,
    )
    orphan = AddressedArtifact.from_json(
        {"value": "orphan"},
        schema_id="bijux.runtime.orphan.v1",
        producer="bijux-canon-runtime:research",
    )
    store.put(orphan)
    report = ArtifactReachabilityValidator(
        database_path=db_path,
        payload_store=store,
    ).validate()
    return db_path, store, report, first, active, orphan


def test_collection_requires_exact_confirmation_and_preserves_holds(
    tmp_path: Path,
    resolved_flow,
) -> None:
    db_path, store, report, superseded, active, orphan = _workspace(
        tmp_path, resolved_flow
    )
    collector = SafeGarbageCollector(database_path=db_path, payload_store=store)
    collector.add_hold(
        hold_id="preserve-history",
        artifact_id=superseded.descriptor.artifact_id,
        reason="historical publication evidence",
        created_at=_NOW,
    )
    plan = collector.plan(
        plan_id="collect-unreferenced",
        report=report,
        policy=RetentionPolicy(
            collect_orphans=True,
            collect_superseded=True,
        ),
        created_at=_NOW,
    )

    assert plan.eligible_artifact_ids == (orphan.descriptor.artifact_id,)
    assert any(
        item.artifact_id == superseded.descriptor.artifact_id
        and item.disposition == "held"
        for item in plan.candidates
    )
    with pytest.raises(GarbageCollectionSafetyError, match="confirmation"):
        collector.apply(
            plan,
            confirmation="apply:wrong",
            backup_root=tmp_path / "backup",
            applied_at=_NOW,
        )
    assert store.load(active.descriptor.artifact_id) == active
    assert store.load(superseded.descriptor.artifact_id) == superseded
    assert store.load(orphan.descriptor.artifact_id) == orphan


def test_collection_apply_verify_and_rollback_preserve_exact_backup(
    tmp_path: Path,
    resolved_flow,
) -> None:
    db_path, store, report, superseded, active, orphan = _workspace(
        tmp_path, resolved_flow
    )
    collector = SafeGarbageCollector(database_path=db_path, payload_store=store)
    plan = collector.plan(
        plan_id="collect-orphan",
        report=report,
        policy=RetentionPolicy(),
        created_at=_NOW,
    )
    backup_root = tmp_path / "backup"

    applied = collector.apply(
        plan,
        confirmation=f"apply:{plan.plan_sha256}",
        backup_root=backup_root,
        applied_at=_NOW,
    )
    assert applied.status == "applied"
    assert not store.artifact_directory(orphan.descriptor.artifact_id).exists()
    assert (
        AtomicFilesystemArtifactPayloadStore(backup_root).load(
            orphan.descriptor.artifact_id
        )
        == orphan
    )
    assert store.load(active.descriptor.artifact_id) == active
    assert store.load(superseded.descriptor.artifact_id) == superseded

    verified = collector.verify(
        plan,
        backup_root=backup_root,
        verified_at=_NOW,
    )
    assert verified.status == "verified"
    rolled_back = collector.rollback(
        plan,
        backup_root=backup_root,
        rolled_back_at=_NOW,
    )
    assert rolled_back.status == "rolled_back"
    assert store.load(orphan.descriptor.artifact_id) == orphan
    connection = duckdb.connect(str(db_path), read_only=True)
    assert connection.execute(
        "SELECT status, backup_root FROM garbage_collection_plans"
    ).fetchone() == ("rolled_back", str(backup_root.resolve()))
    connection.close()


def test_collection_rejects_tampered_plan(tmp_path: Path, resolved_flow) -> None:
    db_path, store, report, _superseded, _active, _orphan = _workspace(
        tmp_path, resolved_flow
    )
    collector = SafeGarbageCollector(database_path=db_path, payload_store=store)
    plan = collector.plan(
        plan_id="collect-orphan",
        report=report,
        policy=RetentionPolicy(),
        created_at=_NOW,
    )
    tampered = replace(plan, reachability_sha256="tampered")
    with pytest.raises(GarbageCollectionSafetyError, match="checksum"):
        collector.apply(
            tampered,
            confirmation=f"apply:{tampered.plan_sha256}",
            backup_root=tmp_path / "backup",
            applied_at=_NOW,
        )
