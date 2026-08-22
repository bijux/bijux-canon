from __future__ import annotations

import hashlib
from pathlib import Path
import shutil

from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.model.execution.run_mode import RunMode
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionWriteStore,
)
from bijux_canon_runtime.runtime.persistence import (
    ArtifactPublicationCoordinator,
    ArtifactReachabilityValidator,
    AtomicFilesystemArtifactPayloadStore,
    PublicationItem,
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
    return db_path, store, coordinator, resolved_flow.manifest.tenant_id, run_id


def _artifact(value: str) -> AddressedArtifact:
    return AddressedArtifact.from_json(
        {"value": value},
        schema_id="bijux.runtime.reachability-fixture.v1",
        producer="bijux-canon-runtime:reachability-test",
    )


def _tree_hashes(root: Path) -> dict[str, tuple[int, str]]:
    return {
        str(path.relative_to(root)): (
            path.stat().st_mtime_ns,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_reachability_classifies_superseded_and_orphan_without_mutation(
    tmp_path: Path,
    resolved_flow,
) -> None:
    db_path, store, coordinator, tenant_id, run_id = _workspace(tmp_path, resolved_flow)
    first = _artifact("first")
    active = _artifact("active")
    orphan = _artifact("orphan")
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
    store.put(orphan)
    before = _tree_hashes(tmp_path)

    validator = ArtifactReachabilityValidator(
        database_path=db_path,
        payload_store=store,
    )
    report = validator.validate()
    repeated = validator.validate()

    assert report == repeated
    assert report.integrity_ok
    assert report.root_artifact_ids == (active.descriptor.artifact_id,)
    assert report.reachable_artifact_ids == (active.descriptor.artifact_id,)
    assert report.superseded_artifact_ids == (first.descriptor.artifact_id,)
    assert report.orphan_artifact_ids == (orphan.descriptor.artifact_id,)
    assert not report.missing_artifact_ids
    assert not report.corrupt_artifact_ids
    assert _tree_hashes(tmp_path) == before


def test_reachability_reports_missing_active_payload(
    tmp_path: Path,
    resolved_flow,
) -> None:
    db_path, store, coordinator, tenant_id, run_id = _workspace(tmp_path, resolved_flow)
    active = _artifact("missing")
    coordinator.publish(
        tenant_id=tenant_id,
        run_id=run_id,
        transaction_id="publish",
        items=(PublicationItem("result/current", 0, active),),
        created_at=_NOW,
        completed_at=_NOW,
    )
    digest = str(active.descriptor.artifact_id).removeprefix("sha256:")
    shutil.rmtree(store.root / "objects" / "sha256" / digest[:2] / digest)

    report = ArtifactReachabilityValidator(
        database_path=db_path,
        payload_store=store,
    ).validate()

    assert report.missing_artifact_ids == (active.descriptor.artifact_id,)
    assert not report.integrity_ok


def test_reachability_reports_corrupt_active_payload(
    tmp_path: Path,
    resolved_flow,
) -> None:
    db_path, store, coordinator, tenant_id, run_id = _workspace(tmp_path, resolved_flow)
    active = _artifact("corrupt")
    coordinator.publish(
        tenant_id=tenant_id,
        run_id=run_id,
        transaction_id="publish",
        items=(PublicationItem("result/current", 0, active),),
        created_at=_NOW,
        completed_at=_NOW,
    )
    digest = str(active.descriptor.artifact_id).removeprefix("sha256:")
    payload_path = store.root / "objects" / "sha256" / digest[:2] / digest / "payload"
    payload_path.write_bytes(b"corrupt")

    report = ArtifactReachabilityValidator(
        database_path=db_path,
        payload_store=store,
    ).validate()

    assert report.corrupt_artifact_ids == (active.descriptor.artifact_id,)
    assert not report.integrity_ok
