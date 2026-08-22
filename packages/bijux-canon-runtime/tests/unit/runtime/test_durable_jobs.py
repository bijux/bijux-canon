# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for the restart-safe asynchronous Runtime job authority."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
from time import sleep

import pytest

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
