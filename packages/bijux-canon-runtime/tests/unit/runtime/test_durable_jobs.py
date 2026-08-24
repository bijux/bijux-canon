# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for the restart-safe asynchronous Runtime job authority."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import threading
from time import sleep

import pytest

from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.model.execution.request_plan import (
    MAX_RUNTIME_TIMEOUT_SECONDS,
)
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.persistence.authoritative_payload_store import (
    AuthoritativeArtifactPayloadStore,
)
from bijux_canon_runtime.runtime.persistence.filesystem_payload_store import (
    AtomicFilesystemArtifactPayloadStore,
)

from bijux_canon_runtime.runtime.execution.durable_jobs import (
    DurableJobCapacityError,
    DurableJobError,
    DurableJobManager,
    DurableJobRequest,
    JobKind,
    JobStatus,
)


def _handlers(
    handler: Callable[
        [DurableJobRequest, Callable[[], bool]],
        Mapping[str, object],
    ],
) -> dict[JobKind, Callable[..., Mapping[str, object]]]:
    return {JobKind.RUN: handler, JobKind.REPLAY: handler}


def _request(
    key: str,
    *,
    value: str = "evidence",
    timeout_seconds: float | None = None,
) -> DurableJobRequest:
    return DurableJobRequest(
        kind=JobKind.RUN,
        idempotency_key=key,
        payload={"value": value},
        timeout_seconds=timeout_seconds,
    )


@pytest.mark.parametrize("timeout_seconds", [float("nan"), float("inf"), 604_801])
def test_job_request_rejects_unrepresentable_timeouts(
    timeout_seconds: float,
) -> None:
    with pytest.raises(ValueError, match="job execution timeout must be finite"):
        _request("invalid-timeout", timeout_seconds=timeout_seconds)


def test_job_request_accepts_the_documented_timeout_limit() -> None:
    request = _request(
        "maximum-timeout", timeout_seconds=MAX_RUNTIME_TIMEOUT_SECONDS
    )

    assert request.timeout_seconds == 604_800


@pytest.mark.parametrize("timeout_seconds", [float("nan"), float("inf"), 604_801])
def test_job_wait_rejects_unrepresentable_timeouts(
    tmp_path: Path,
    timeout_seconds: float,
) -> None:
    with DurableJobManager(
        tmp_path / "jobs.sqlite3", handlers=_handlers(lambda _request, _cancel: {})
    ) as manager:
        with pytest.raises(ValueError, match="job wait timeout must be finite"):
            manager.wait("job_v1_missing", timeout_seconds=timeout_seconds)


def test_job_submission_is_idempotent_and_survives_restart(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def handler(
        request: DurableJobRequest,
        _is_cancelled: Callable[[], bool],
    ) -> Mapping[str, object]:
        calls.append(request.idempotency_key)
        return {"accepted": request.payload["value"]}

    database = tmp_path / "jobs.sqlite3"
    request = _request("stable-submission")
    with DurableJobManager(database, handlers=_handlers(handler)) as manager:
        submitted = manager.submit(request)
        completed = manager.wait(submitted.job_id, timeout_seconds=2.0)
        repeated = manager.submit(request)

        assert submitted.job_id == request.job_id
        assert completed.status is JobStatus.SUCCEEDED
        assert completed.attempt_count == 1
        assert completed.request_artifact_id.startswith("sha256:")
        assert completed.result_artifact_id is not None
        assert repeated == completed
        assert manager.result(request.job_id) == {"accepted": "evidence"}
        assert calls == ["stable-submission"]
        with pytest.raises(
            DurableJobError,
            match="idempotency key is already bound",
        ):
            manager.submit(_request("stable-submission", value="different"))

    with DurableJobManager(database, handlers=_handlers(handler)) as restarted:
        assert restarted.status(request.job_id) == completed
        assert restarted.result(request.job_id) == {"accepted": "evidence"}
        assert calls == ["stable-submission"]


def test_durable_result_depends_on_every_artifact_identity_it_returns(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "runtime.duckdb"
    filesystem = AtomicFilesystemArtifactPayloadStore(tmp_path / "cas")
    payload_store = AuthoritativeArtifactPayloadStore(
        payload_store=filesystem,
        database_path=database_path,
    )
    evidence = AddressedArtifact.from_json(
        {"evidence": "retained"},
        schema_id="bijux.runtime.job-evidence.v1",
        producer="bijux-canon-runtime:test",
    )
    payload_store.put(evidence)

    def handler(
        _request: DurableJobRequest,
        _is_cancelled: Callable[[], bool],
    ) -> Mapping[str, object]:
        return {"artifact_id": str(evidence.descriptor.artifact_id)}

    with DurableJobManager(
        database_path,
        handlers=_handlers(handler),
        payload_store=payload_store,
    ) as manager:
        submitted = manager.submit(_request("linked-result"))
        completed = manager.wait(submitted.job_id, timeout_seconds=2.0)

        assert completed.result_artifact_id is not None
        result_artifact = filesystem.load(ArtifactID(completed.result_artifact_id))
        assert result_artifact.descriptor.dependencies == tuple(
            sorted(
                (
                    ArtifactID(completed.request_artifact_id),
                    evidence.descriptor.artifact_id,
                )
            )
        )
        assert manager.result(submitted.job_id) == {
            "artifact_id": str(evidence.descriptor.artifact_id)
        }


def test_legacy_sqlite_jobs_migrate_to_duckdb_and_cas(tmp_path: Path) -> None:
    legacy_path = tmp_path / "jobs.sqlite"
    request = _request("legacy-completed")
    result = {"accepted": "legacy evidence"}
    with sqlite3.connect(legacy_path) as legacy:
        legacy.execute(
            """
            CREATE TABLE runtime_jobs (
                job_id TEXT PRIMARY KEY, kind TEXT NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE,
                request_sha256 TEXT NOT NULL, payload_json TEXT NOT NULL,
                status TEXT NOT NULL, cancel_requested INTEGER NOT NULL,
                attempt_count INTEGER NOT NULL, submitted_at TEXT NOT NULL,
                started_at TEXT, finished_at TEXT, result_json TEXT,
                error_type TEXT, error_message TEXT
            )
            """
        )
        legacy.execute(
            """
            INSERT INTO runtime_jobs VALUES (
                ?, ?, ?, ?, ?, 'succeeded', 0, 1, ?, ?, ?, ?, NULL, NULL
            )
            """,
            (
                request.job_id,
                request.kind.value,
                request.idempotency_key,
                request.request_sha256,
                request.payload_json,
                "2026-08-22T00:00:00+00:00",
                "2026-08-22T00:00:01+00:00",
                "2026-08-22T00:00:02+00:00",
                json.dumps(result, sort_keys=True, separators=(",", ":")),
            ),
        )
    database_path = tmp_path / "runtime.duckdb"
    filesystem = AtomicFilesystemArtifactPayloadStore(tmp_path / "cas")
    payload_store = AuthoritativeArtifactPayloadStore(
        payload_store=filesystem,
        database_path=database_path,
    )

    with DurableJobManager(
        database_path,
        handlers=_handlers(lambda _request, _cancelled: {}),
        payload_store=payload_store,
        legacy_database_path=legacy_path,
    ) as manager:
        snapshot = manager.status(request.job_id)
        assert snapshot.status is JobStatus.SUCCEEDED
        assert snapshot.result == result
        assert filesystem.load(
            ArtifactID(snapshot.request_artifact_id)
        ).descriptor.schema_id == "bijux.runtime.durable-job-request.v1"
        assert snapshot.result_artifact_id is not None

    legacy_path.unlink()
    with DurableJobManager(
        database_path,
        handlers=_handlers(lambda _request, _cancelled: {}),
        payload_store=payload_store,
    ) as restarted:
        assert restarted.result(request.job_id) == result


def test_failed_job_retains_exact_error_and_attempt_count(tmp_path: Path) -> None:
    def handler(
        _request: DurableJobRequest,
        _is_cancelled: Callable[[], bool],
    ) -> Mapping[str, object]:
        raise LookupError("provider refused request")

    with DurableJobManager(
        tmp_path / "jobs.sqlite3",
        handlers=_handlers(handler),
    ) as manager:
        submitted = manager.submit(_request("failed-submission"))
        completed = manager.wait(submitted.job_id, timeout_seconds=2.0)

        assert completed.status is JobStatus.FAILED
        assert completed.attempt_count == 1
        assert completed.error_type == "LookupError"
        assert completed.error_message == "provider refused request"
        with pytest.raises(
            DurableJobError,
            match="ended as failed: provider refused request",
        ):
            manager.result(submitted.job_id)


def test_queued_job_can_be_cancelled_without_invoking_handler(
    tmp_path: Path,
) -> None:
    first_started = threading.Event()
    release_first = threading.Event()
    calls: list[str] = []

    def handler(
        request: DurableJobRequest,
        _is_cancelled: Callable[[], bool],
    ) -> Mapping[str, object]:
        calls.append(request.idempotency_key)
        first_started.set()
        if not release_first.wait(timeout=2.0):
            raise TimeoutError("test did not release the worker")
        return {"completed": request.idempotency_key}

    manager = DurableJobManager(
        tmp_path / "jobs.sqlite3",
        handlers=_handlers(handler),
        max_workers=1,
    )
    try:
        first = manager.submit(_request("running-job"))
        assert first_started.wait(timeout=2.0)
        queued = manager.submit(_request("queued-job"))
        cancelled = manager.cancel(queued.job_id)

        assert cancelled.status is JobStatus.CANCELLED
        assert cancelled.attempt_count == 0
        assert cancelled.error_type == "DurableJobCancelled"
        assert calls == ["running-job"]
    finally:
        release_first.set()
        manager.close()

    assert calls == ["running-job"]
    assert manager.status(first.job_id).status is JobStatus.SUCCEEDED


def test_running_job_retains_partial_result_when_cancelled(
    tmp_path: Path,
) -> None:
    started = threading.Event()
    release = threading.Event()

    def handler(
        _request: DurableJobRequest,
        is_cancelled: Callable[[], bool],
    ) -> Mapping[str, object]:
        started.set()
        if not release.wait(timeout=2.0):
            raise TimeoutError("test did not release the worker")
        return {"partial_evidence": True, "cancel_observed": is_cancelled()}

    manager = DurableJobManager(
        tmp_path / "jobs.sqlite3",
        handlers=_handlers(handler),
    )
    try:
        submitted = manager.submit(_request("running-cancellation"))
        assert started.wait(timeout=2.0)
        requested = manager.cancel(submitted.job_id)
        release.set()
        completed = manager.wait(submitted.job_id, timeout_seconds=2.0)

        assert requested.cancel_requested
        assert completed.status is JobStatus.CANCELLED
        assert completed.result == {
            "cancel_observed": True,
            "partial_evidence": True,
        }
        assert completed.error_type == "DurableJobCancelled"
        assert completed.error_message == (
            "durable job was cancelled after partial evidence"
        )
    finally:
        release.set()
        manager.close()


def test_job_deadline_is_classified_separately_from_failure(
    tmp_path: Path,
) -> None:
    def handler(
        _request: DurableJobRequest,
        is_cancelled: Callable[[], bool],
    ) -> Mapping[str, object]:
        sleep(0.03)
        return {"deadline_observed": is_cancelled()}

    with DurableJobManager(
        tmp_path / "jobs.sqlite3",
        handlers=_handlers(handler),
    ) as manager:
        submitted = manager.submit(_request("deadline", timeout_seconds=0.005))
        completed = manager.wait(submitted.job_id, timeout_seconds=2.0)

        assert completed.status is JobStatus.TIMED_OUT
        assert completed.result == {"deadline_observed": True}
        assert completed.error_type == "DurableJobTimedOut"
        assert completed.error_message == (
            "durable job deadline exceeded after partial evidence"
        )


def test_job_queue_and_request_payload_admission_are_bounded(tmp_path: Path) -> None:
    started = threading.Event()
    release = threading.Event()

    def handler(
        request: DurableJobRequest,
        _is_cancelled: Callable[[], bool],
    ) -> Mapping[str, object]:
        started.set()
        if not release.wait(timeout=2.0):
            raise TimeoutError("test did not release the worker")
        return {"completed": request.idempotency_key}

    manager = DurableJobManager(
        tmp_path / "jobs.sqlite3",
        handlers=_handlers(handler),
        max_workers=1,
        max_pending_jobs=2,
        max_request_bytes=64,
    )
    try:
        first = manager.submit(_request("capacity-running"))
        assert started.wait(timeout=2.0)
        second = manager.submit(_request("capacity-queued"))

        with pytest.raises(DurableJobCapacityError, match="max_pending_jobs=2"):
            manager.submit(_request("capacity-refused"))
        with pytest.raises(DurableJobCapacityError, match="max_request_bytes=64"):
            manager.submit(
                DurableJobRequest(
                    kind=JobKind.RUN,
                    idempotency_key="oversized-request",
                    payload={"value": "x" * 80},
                )
            )

        release.set()
        assert (
            manager.wait(first.job_id, timeout_seconds=2.0).status
            is JobStatus.SUCCEEDED
        )
        assert (
            manager.wait(second.job_id, timeout_seconds=2.0).status
            is JobStatus.SUCCEEDED
        )
    finally:
        release.set()
        manager.close()


def test_oversized_job_result_is_a_typed_terminal_failure(tmp_path: Path) -> None:
    def handler(
        _request: DurableJobRequest,
        _is_cancelled: Callable[[], bool],
    ) -> Mapping[str, object]:
        return {"value": "x" * 80}

    with DurableJobManager(
        tmp_path / "jobs.sqlite3",
        handlers=_handlers(handler),
        max_result_bytes=64,
    ) as manager:
        submitted = manager.submit(_request("oversized-result"))
        completed = manager.wait(submitted.job_id, timeout_seconds=2.0)

    assert completed.status is JobStatus.FAILED
    assert completed.error_type == "DurableJobCapacityError"
    assert completed.error_message == "durable job result exceeds max_result_bytes=64"
    assert completed.result is None


def test_concurrent_idempotent_submission_admits_one_job_transition(
    tmp_path: Path,
) -> None:
    release = threading.Event()

    def handler(
        request: DurableJobRequest,
        _is_cancelled: Callable[[], bool],
    ) -> Mapping[str, object]:
        if not release.wait(timeout=2.0):
            raise TimeoutError("test did not release the worker")
        return {"completed": request.idempotency_key}

    request = _request("concurrent-idempotency")
    manager = DurableJobManager(
        tmp_path / "jobs.sqlite3",
        handlers=_handlers(handler),
        max_workers=1,
        max_pending_jobs=2,
    )
    try:
        with ThreadPoolExecutor(max_workers=8) as callers:
            snapshots = tuple(
                callers.map(lambda _index: manager.submit(request), range(8))
            )
        release.set()
        completed = manager.wait(request.job_id, timeout_seconds=2.0)
    finally:
        release.set()
        manager.close()

    assert {snapshot.job_id for snapshot in snapshots} == {request.job_id}
    assert completed.status is JobStatus.SUCCEEDED
    assert completed.attempt_count == 1
