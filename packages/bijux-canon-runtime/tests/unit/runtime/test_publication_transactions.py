from __future__ import annotations

import errno
from pathlib import Path

import duckdb
import pytest

from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.model.execution.run_mode import RunMode
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionWriteStore,
)
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.persistence import (
    ArtifactPublicationCoordinator,
    AtomicFilesystemArtifactPayloadStore,
    MetadataIntegrityError,
    PublicationItem,
    PublicationRecoveryError,
)

_NOW = "2026-08-22T00:00:00+00:00"
_LATER = "2026-08-22T00:00:01+00:00"


def _coordinator(tmp_path: Path, resolved_flow):
    db_path = tmp_path / "runtime.duckdb"
    execution = DuckDBExecutionWriteStore(db_path)
    run_id = execution.save_run(
        trace=None,
        plan=resolved_flow.plan,
        mode=RunMode.DRY_RUN,
    )
    execution._store.close()
    payload_root = tmp_path / "cas"
    return (
        ArtifactPublicationCoordinator(
            payload_store=AtomicFilesystemArtifactPayloadStore(payload_root),
            database_path=db_path,
        ),
        payload_root,
        db_path,
        resolved_flow.manifest.tenant_id,
        run_id,
    )


def _item(payload: str, *, revision: int = 0) -> PublicationItem:
    return PublicationItem(
        logical_artifact_id="research/current",
        revision=revision,
        artifact=AddressedArtifact.from_json(
            {"payload": payload},
            schema_id="bijux.runtime.research-result.v1",
            producer="bijux-canon-runtime:research",
        ),
    )


def test_prepared_publication_recovers_after_restart(
    tmp_path: Path, resolved_flow
) -> None:
    coordinator, payload_root, db_path, tenant_id, run_id = _coordinator(
        tmp_path, resolved_flow
    )
    prepared = coordinator.prepare(
        tenant_id=tenant_id,
        run_id=run_id,
        transaction_id="publish-1",
        items=(_item("exact result"),),
        created_at=_NOW,
    )
    assert prepared.status == "prepared"
    connection = duckdb.connect(str(db_path), read_only=True)
    assert connection.execute("SELECT count(*) FROM artifact_payloads").fetchone() == (
        0,
    )
    assert connection.execute(
        "SELECT count(*) FROM artifact_references"
    ).fetchone() == (0,)
    connection.close()

    restarted = ArtifactPublicationCoordinator(
        payload_store=AtomicFilesystemArtifactPayloadStore(payload_root),
        database_path=db_path,
    )
    committed = restarted.commit(
        tenant_id=tenant_id,
        run_id=run_id,
        transaction_id="publish-1",
        completed_at=_LATER,
    )

    assert committed.status == "committed"
    connection = duckdb.connect(str(db_path), read_only=True)
    assert connection.execute("SELECT count(*) FROM artifact_payloads").fetchone() == (
        1,
    )
    assert connection.execute(
        "SELECT reference_state FROM artifact_references"
    ).fetchone() == ("active",)
    connection.close()


def test_publication_retry_is_idempotent_and_conflicting_intent_fails(
    tmp_path: Path,
    resolved_flow,
) -> None:
    coordinator, _payload_root, _db_path, tenant_id, run_id = _coordinator(
        tmp_path, resolved_flow
    )
    item = _item("exact result")
    first = coordinator.publish(
        tenant_id=tenant_id,
        run_id=run_id,
        transaction_id="publish-1",
        items=(item,),
        created_at=_NOW,
        completed_at=_LATER,
    )
    retry = coordinator.publish(
        tenant_id=tenant_id,
        run_id=run_id,
        transaction_id="publish-1",
        items=(item,),
        created_at=_NOW,
        completed_at=_LATER,
    )
    assert retry == first

    with pytest.raises(MetadataIntegrityError, match="conflicting intent"):
        coordinator.prepare(
            tenant_id=tenant_id,
            run_id=run_id,
            transaction_id="publish-1",
            items=(_item("different result"),),
            created_at=_NOW,
        )


def test_missing_prepared_blob_aborts_recovery(tmp_path: Path, resolved_flow) -> None:
    coordinator, payload_root, db_path, tenant_id, run_id = _coordinator(
        tmp_path, resolved_flow
    )
    item = _item("exact result")
    coordinator.prepare(
        tenant_id=tenant_id,
        run_id=run_id,
        transaction_id="publish-1",
        items=(item,),
        created_at=_NOW,
    )
    digest = str(item.artifact.descriptor.artifact_id).removeprefix("sha256:")
    payload_path = payload_root / "objects" / "sha256" / digest[:2] / digest / "payload"
    payload_path.write_bytes(b"corrupt after prepare")

    with pytest.raises(PublicationRecoveryError, match="durable payload validation"):
        coordinator.commit(
            tenant_id=tenant_id,
            run_id=run_id,
            transaction_id="publish-1",
            completed_at=_LATER,
        )
    connection = duckdb.connect(str(db_path), read_only=True)
    assert connection.execute(
        "SELECT status, failure_reason FROM publication_transactions"
    ).fetchone() == ("aborted", "durable payload unavailable or invalid")
    assert connection.execute(
        "SELECT count(*) FROM artifact_references"
    ).fetchone() == (0,)
    connection.close()


def test_corrupt_candidate_retains_last_good_publication_and_forensic_state(
    tmp_path: Path, resolved_flow
) -> None:
    coordinator, payload_root, db_path, tenant_id, run_id = _coordinator(
        tmp_path, resolved_flow
    )
    coordinator.publish(
        tenant_id=tenant_id,
        run_id=run_id,
        transaction_id="publish-good",
        items=(_item("last good", revision=0),),
        created_at=_NOW,
        completed_at=_LATER,
    )
    candidate = _item("tampered candidate", revision=1)
    coordinator.prepare(
        tenant_id=tenant_id,
        run_id=run_id,
        transaction_id="publish-corrupt",
        items=(candidate,),
        created_at=_LATER,
    )
    digest = str(candidate.artifact.descriptor.artifact_id).removeprefix("sha256:")
    payload_path = payload_root / "objects" / "sha256" / digest[:2] / digest / "payload"
    payload_path.write_bytes(b"modified candidate bytes")

    with pytest.raises(PublicationRecoveryError, match="durable payload validation"):
        coordinator.commit(
            tenant_id=tenant_id,
            run_id=run_id,
            transaction_id="publish-corrupt",
            completed_at=_LATER,
        )

    connection = duckdb.connect(str(db_path), read_only=True)
    assert connection.execute(
        "SELECT revision, reference_state FROM artifact_references ORDER BY revision"
    ).fetchall() == [(0, "active")]
    assert connection.execute(
        "SELECT transaction_id, status, failure_reason "
        "FROM publication_transactions ORDER BY transaction_id"
    ).fetchall() == [
        ("publish-corrupt", "aborted", "durable payload unavailable or invalid"),
        ("publish-good", "committed", None),
    ]
    connection.close()


def test_logical_activation_advances_once_without_split_brain(
    tmp_path: Path,
    resolved_flow,
) -> None:
    coordinator, _payload_root, db_path, tenant_id, run_id = _coordinator(
        tmp_path, resolved_flow
    )
    coordinator.publish(
        tenant_id=tenant_id,
        run_id=run_id,
        transaction_id="publish-1",
        items=(_item("first", revision=0),),
        created_at=_NOW,
        completed_at=_LATER,
    )
    coordinator.publish(
        tenant_id=tenant_id,
        run_id=run_id,
        transaction_id="publish-2",
        items=(_item("second", revision=1),),
        created_at=_LATER,
        completed_at=_LATER,
    )
    connection = duckdb.connect(str(db_path), read_only=True)
    assert connection.execute(
        "SELECT revision, reference_state FROM artifact_references ORDER BY revision"
    ).fetchall() == [(0, "superseded"), (1, "active")]
    connection.close()

    with pytest.raises(PublicationRecoveryError, match="could not be activated"):
        coordinator.publish(
            tenant_id=tenant_id,
            run_id=run_id,
            transaction_id="publish-split",
            items=(_item("split brain", revision=1),),
            created_at=_LATER,
            completed_at=_LATER,
        )


def test_missing_dependency_never_creates_metadata_intent(
    tmp_path: Path,
    resolved_flow,
) -> None:
    coordinator, _payload_root, db_path, tenant_id, run_id = _coordinator(
        tmp_path, resolved_flow
    )
    artifact = AddressedArtifact.from_json(
        {"payload": "derived"},
        schema_id="bijux.runtime.derived.v1",
        producer="bijux-canon-runtime:research",
        dependencies=(ArtifactID("sha256:" + "a" * 64),),
    )
    with pytest.raises(KeyError, match="payload not found"):
        coordinator.prepare(
            tenant_id=tenant_id,
            run_id=run_id,
            transaction_id="publish-missing",
            items=(PublicationItem("derived/current", 0, artifact),),
            created_at=_NOW,
        )
    connection = duckdb.connect(str(db_path), read_only=True)
    assert connection.execute(
        "SELECT count(*) FROM publication_transactions"
    ).fetchone() == (0,)
    connection.close()


def test_disk_exhaustion_never_advances_publication_metadata(
    tmp_path: Path,
    resolved_flow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator, payload_root, db_path, tenant_id, run_id = _coordinator(
        tmp_path, resolved_flow
    )
    retained = _item("last good", revision=0)
    coordinator.publish(
        tenant_id=tenant_id,
        run_id=run_id,
        transaction_id="publish-good",
        items=(retained,),
        created_at=_NOW,
        completed_at=_LATER,
    )

    def exhaust_disk(path: Path, _payload: bytes) -> None:
        raise OSError(errno.ENOSPC, "injected storage exhaustion", path)

    monkeypatch.setattr(coordinator._payload_store, "_write_durable", exhaust_disk)
    with pytest.raises(OSError, match="injected storage exhaustion") as raised:
        coordinator.publish(
            tenant_id=tenant_id,
            run_id=run_id,
            transaction_id="publish-no-space",
            items=(_item("not durable", revision=1),),
            created_at=_LATER,
            completed_at=_LATER,
        )

    assert raised.value.errno == errno.ENOSPC
    assert list((payload_root / "staging").iterdir()) == []
    connection = duckdb.connect(str(db_path), read_only=True)
    assert connection.execute(
        "SELECT transaction_id, status FROM publication_transactions"
    ).fetchall() == [("publish-good", "committed")]
    assert connection.execute(
        "SELECT revision, target_artifact_id, reference_state "
        "FROM artifact_references"
    ).fetchall() == [
        (0, str(retained.artifact.descriptor.artifact_id), "active")
    ]
    connection.close()
