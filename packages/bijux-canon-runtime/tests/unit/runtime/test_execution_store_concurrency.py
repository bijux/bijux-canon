from __future__ import annotations

import json
import multiprocessing
import os
from pathlib import Path
import time
from typing import Any

import duckdb
import pytest

from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.model.execution.run_mode import RunMode
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionReadStore,
    DuckDBExecutionStore,
    DuckDBExecutionWriteStore,
    ExecutionStoreLockTimeout,
    ExecutionStoreLockUpgradeError,
)
from bijux_canon_runtime.ontology.ids import RunID, TenantID
from bijux_canon_runtime.runtime.persistence import (
    ArtifactPublicationCoordinator,
    ArtifactReachabilityValidator,
    AtomicFilesystemArtifactPayloadStore,
    PublicationItem,
)


def _hold_reader(database: str, ready: Any, release: Any) -> None:
    store = DuckDBExecutionReadStore(
        Path(database),
        lock_timeout_seconds=1.0,
    )
    ready.set()
    release.wait(5.0)
    store._store.close()


def _crash_writer(database: str, ready: Any) -> None:
    store = DuckDBExecutionStore(Path(database), lock_timeout_seconds=1.0)
    ready.set()
    assert store._lease is not None
    os._exit(17)


def _hold_writer(database: str, ready: Any, release: Any) -> None:
    store = DuckDBExecutionStore(Path(database), lock_timeout_seconds=1.0)
    ready.set()
    release.wait(5.0)
    store.close()


def _publish_same_intent(
    database: str,
    cas_root: str,
    tenant_id: str,
    run_id: str,
    start: Any,
    outcomes: Any,
) -> None:
    artifact = AddressedArtifact.from_json(
        {"answer": "steppe ancestry contributed to European populations"},
        schema_id="bijux.runtime.answer.v1",
        producer="bijux-canon-reason:answer",
    )
    coordinator = ArtifactPublicationCoordinator(
        payload_store=AtomicFilesystemArtifactPayloadStore(Path(cas_root)),
        database_path=Path(database),
        lock_timeout_seconds=2.0,
    )
    start.wait(5.0)
    result = coordinator.publish(
        tenant_id=TenantID(tenant_id),
        run_id=RunID(run_id),
        transaction_id="publish-reviewed-answer",
        items=(PublicationItem("answer/current", 0, artifact),),
        created_at="2026-08-22T00:00:00+00:00",
        completed_at="2026-08-22T00:00:01+00:00",
    )
    outcomes.put((result.status, result.intent_hash))


def test_readers_share_snapshot_lease_and_writer_wait_is_bounded(
    tmp_path: Path,
) -> None:
    database = tmp_path / "runtime.duckdb"
    seed = DuckDBExecutionStore(database)
    seed.close()
    context = multiprocessing.get_context("spawn")
    first_ready = context.Event()
    second_ready = context.Event()
    release = context.Event()
    readers = (
        context.Process(
            target=_hold_reader,
            args=(str(database), first_ready, release),
        ),
        context.Process(
            target=_hold_reader,
            args=(str(database), second_ready, release),
        ),
    )
    for process in readers:
        process.start()
    assert first_ready.wait(3.0)
    assert second_ready.wait(3.0)

    started = time.monotonic()
    try:
        DuckDBExecutionStore(database, lock_timeout_seconds=0.1)
    except ExecutionStoreLockTimeout:
        pass
    else:
        raise AssertionError("writer acquired while snapshot readers were active")
    elapsed = time.monotonic() - started
    assert 0.08 <= elapsed < 0.75

    release.set()
    for process in readers:
        process.join(3.0)
        assert process.exitcode == 0
    writer = DuckDBExecutionStore(database, lock_timeout_seconds=1.0)
    writer.close()


def test_kernel_lease_recovers_crashed_writer_owner(tmp_path: Path) -> None:
    database = tmp_path / "runtime.duckdb"
    seed = DuckDBExecutionStore(database)
    seed.close()
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    process = context.Process(target=_crash_writer, args=(str(database), ready))
    process.start()
    assert ready.wait(3.0)
    process.join(3.0)
    assert process.exitcode == 17

    recovered = DuckDBExecutionStore(database, lock_timeout_seconds=1.0)
    lock_record = json.loads(
        database.with_suffix(".duckdb.lock").read_text(encoding="utf-8")
    )
    assert lock_record["recovered_stale_owner"] is True
    assert lock_record["pid"] == os.getpid()
    recovered.close()


def test_local_reader_to_writer_upgrade_fails_explicitly(tmp_path: Path) -> None:
    database = tmp_path / "runtime.duckdb"
    seed = DuckDBExecutionStore(database)
    seed.close()
    reader = DuckDBExecutionReadStore(database)

    with pytest.raises(
        ExecutionStoreLockUpgradeError,
        match="process holds readers",
    ):
        DuckDBExecutionStore(database, lock_timeout_seconds=0.1)

    reader._store.close()


def test_reachability_reader_obeys_writer_lease(tmp_path: Path) -> None:
    database = tmp_path / "runtime.duckdb"
    seed = DuckDBExecutionStore(database)
    seed.close()
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    release = context.Event()
    writer = context.Process(
        target=_hold_writer,
        args=(str(database), ready, release),
    )
    writer.start()
    assert ready.wait(3.0)

    with pytest.raises(ExecutionStoreLockTimeout):
        ArtifactReachabilityValidator(
            database_path=database,
            payload_store=AtomicFilesystemArtifactPayloadStore(tmp_path / "cas"),
            lock_timeout_seconds=0.1,
        ).validate()

    release.set()
    writer.join(3.0)
    assert writer.exitcode == 0


def test_multiprocess_publication_has_one_atomic_activation(
    tmp_path: Path,
    resolved_flow,
) -> None:
    database = tmp_path / "runtime.duckdb"
    execution = DuckDBExecutionWriteStore(database)
    run_id = execution.save_run(
        trace=None,
        plan=resolved_flow.plan,
        mode=RunMode.DRY_RUN,
    )
    execution._store.close()
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    outcomes = context.Queue()
    workers = tuple(
        context.Process(
            target=_publish_same_intent,
            args=(
                str(database),
                str(tmp_path / "cas"),
                str(resolved_flow.manifest.tenant_id),
                str(run_id),
                start,
                outcomes,
            ),
        )
        for _ in range(3)
    )
    for process in workers:
        process.start()
    start.set()
    for process in workers:
        process.join(5.0)
        assert process.exitcode == 0
    results = [outcomes.get(timeout=1.0) for _ in workers]
    assert {status for status, _intent_hash in results} == {"committed"}
    assert len({intent_hash for _status, intent_hash in results}) == 1

    connection = duckdb.connect(str(database), read_only=True)
    try:
        transaction = connection.execute(
            """
            SELECT count(*), min(status), max(status)
            FROM publication_transactions
            WHERE transaction_id = 'publish-reviewed-answer'
            """
        ).fetchone()
        active = connection.execute(
            """
            SELECT count(*), count(DISTINCT target_artifact_id)
            FROM artifact_references
            WHERE logical_artifact_id = 'answer/current'
              AND reference_state = 'active'
            """
        ).fetchone()
    finally:
        connection.close()
    assert transaction == (1, "committed", "committed")
    assert active == (1, 1)
