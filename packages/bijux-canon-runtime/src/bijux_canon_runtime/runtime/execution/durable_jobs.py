# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Asynchronous restart-safe run and replay jobs backed by SQLite."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
from typing import Protocol

from bijux_canon_runtime.model.artifact import canonical_json_bytes


class DurableJobError(RuntimeError):
    """A durable job request or state transition is invalid."""


class DurableJobCancelled(DurableJobError):
    """A caller cancelled a durable job before successful completion."""


class DurableJobTimedOut(DurableJobError):
    """A durable job exceeded its persisted execution deadline."""


class JobKind(StrEnum):
    """Asynchronous Runtime job kinds."""

    RUN = "run"
    REPLAY = "replay"


class JobStatus(StrEnum):
    """Durable job lifecycle states."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"

    @property
    def terminal(self) -> bool:
        """Return whether the job cannot transition again."""
        return self in {
            self.SUCCEEDED,
            self.FAILED,
            self.CANCELLED,
            self.TIMED_OUT,
        }


@dataclass(frozen=True, slots=True)
class DurableJobRequest:
    """Canonical submission payload with caller-owned idempotency."""

    kind: JobKind
    idempotency_key: str
    payload: Mapping[str, object]
    timeout_seconds: float | None = None
    _payload_json: str = field(init=False, repr=False, compare=False)
    _request_sha256: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.kind, JobKind):
            raise TypeError("job kind must be a JobKind")
        if not self.idempotency_key.strip():
            raise ValueError("job idempotency key must not be empty")
        if self.idempotency_key != self.idempotency_key.strip():
            raise ValueError("job idempotency key must not have surrounding whitespace")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("job execution timeout must be positive")
        encoded = canonical_json_bytes(dict(self.payload))
        payload = json.loads(encoded)
        if not isinstance(payload, dict):
            raise TypeError("job payload must be a JSON object")
        payload_json = encoded.decode("utf-8")
        object.__setattr__(self, "payload", payload)
        object.__setattr__(self, "_payload_json", payload_json)
        identity_payload: object = payload
        if self.timeout_seconds is not None:
            identity_payload = {
                "payload": payload,
                "timeout_seconds": self.timeout_seconds,
            }
        object.__setattr__(
            self,
            "_request_sha256",
            hashlib.sha256(canonical_json_bytes(identity_payload)).hexdigest(),
        )

    @property
    def request_sha256(self) -> str:
        """Return the complete immutable request payload identity."""
        return self._request_sha256

    @property
    def payload_json(self) -> str:
        """Return the canonical payload captured when the request was created."""
        return self._payload_json

    @property
    def job_id(self) -> str:
        """Return a stable ID independent of worker process and submission time."""
        payload = {
            "idempotency_key": self.idempotency_key,
            "kind": self.kind.value,
            "request_sha256": self.request_sha256,
            "schema_version": "bijux.runtime.durable-job.v1",
        }
        digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
        return f"job_v1_{digest}"


@dataclass(frozen=True, slots=True)
class DurableJobSnapshot:
    """Transport-neutral durable status returned without worker internals."""

    job_id: str
    kind: JobKind
    idempotency_key: str
    request_sha256: str
    status: JobStatus
    cancel_requested: bool
    attempt_count: int
    submitted_at: str
    started_at: str | None
    finished_at: str | None
    deadline_at: str | None
    timeout_seconds: float | None
    result: dict[str, object] | None
    error_type: str | None
    error_message: str | None


class DurableJobHandler(Protocol):
    """Cooperative execution function reconstructed by the composition root."""

    def __call__(
        self,
        request: DurableJobRequest,
        is_cancelled: Callable[[], bool],
    ) -> Mapping[str, object]:
        """Execute one job and return canonical result metadata."""
        ...


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DurableJobManager:
    """Submit, recover, inspect, cancel, and await durable Runtime jobs."""

    def __init__(
        self,
        database_path: Path,
        *,
        handlers: Mapping[JobKind, DurableJobHandler],
        max_workers: int = 4,
    ) -> None:
        if not database_path.is_absolute():
            raise ValueError("durable job database path must be absolute")
        if max_workers < 1:
            raise ValueError("durable job worker count must be positive")
        missing = set(JobKind).difference(handlers)
        if missing:
            raise ValueError(
                "durable job handlers are missing: "
                + ", ".join(sorted(item.value for item in missing))
            )
        self._path = database_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._handlers = dict(handlers)
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._condition = threading.Condition()
        self._scheduled: set[str] = set()
        self._closed = False
        self._initialize()
        self._recover_interrupted_jobs()

    def submit(self, request: DurableJobRequest) -> DurableJobSnapshot:
        """Commit a queued job and return its stable ID before execution finishes."""
        self._ensure_open()
        payload_json = request.payload_json
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT job_id, kind, request_sha256, payload_json,
                       timeout_seconds
                FROM runtime_jobs WHERE idempotency_key = ?
                """,
                (request.idempotency_key,),
            ).fetchone()
            if existing is not None:
                if existing != (
                    request.job_id,
                    request.kind.value,
                    request.request_sha256,
                    payload_json,
                    request.timeout_seconds,
                ):
                    connection.execute("ROLLBACK")
                    raise DurableJobError(
                        "idempotency key is already bound to another request"
                    )
                connection.execute("COMMIT")
                snapshot = self.status(request.job_id)
                if not snapshot.status.terminal:
                    self._schedule(request.job_id)
                return snapshot
            submitted_at = _now()
            deadline_at = (
                None
                if request.timeout_seconds is None
                else (
                    datetime.fromisoformat(submitted_at)
                    + timedelta(seconds=request.timeout_seconds)
                ).isoformat()
            )
            connection.execute(
                """
                INSERT INTO runtime_jobs (
                    job_id, kind, idempotency_key, request_sha256, payload_json,
                    status, cancel_requested, attempt_count, submitted_at,
                    started_at, finished_at, deadline_at, timeout_seconds,
                    result_json, error_type, error_message
                ) VALUES (
                    ?, ?, ?, ?, ?, 'queued', 0, 0, ?, NULL, NULL, ?, ?,
                    NULL, NULL, NULL
                )
                """,
                (
                    request.job_id,
                    request.kind.value,
                    request.idempotency_key,
                    request.request_sha256,
                    payload_json,
                    submitted_at,
                    deadline_at,
                    request.timeout_seconds,
                ),
            )
            connection.execute("COMMIT")
        snapshot = self.status(request.job_id)
        self._schedule(request.job_id)
        return snapshot

    def status(self, job_id: str) -> DurableJobSnapshot:
        """Read current durable status directly from the authority database."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT job_id, kind, idempotency_key, request_sha256, status,
                       cancel_requested, attempt_count, submitted_at, started_at,
                       finished_at, deadline_at, timeout_seconds, result_json,
                       error_type, error_message
                FROM runtime_jobs WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"durable job not found: {job_id}")
        return DurableJobSnapshot(
            job_id=row[0],
            kind=JobKind(row[1]),
            idempotency_key=row[2],
            request_sha256=row[3],
            status=JobStatus(row[4]),
            cancel_requested=bool(row[5]),
            attempt_count=int(row[6]),
            submitted_at=row[7],
            started_at=row[8],
            finished_at=row[9],
            deadline_at=row[10],
            timeout_seconds=row[11],
            result=None if row[12] is None else json.loads(row[12]),
            error_type=row[13],
            error_message=row[14],
        )

    def result(self, job_id: str) -> dict[str, object]:
        """Return a successful result or classify the current terminal state."""
        snapshot = self.status(job_id)
        if snapshot.status is JobStatus.SUCCEEDED:
            assert snapshot.result is not None
            return snapshot.result
        if not snapshot.status.terminal:
            raise DurableJobError("durable job has not reached a terminal state")
        raise DurableJobError(
            f"durable job ended as {snapshot.status.value}: "
            f"{snapshot.error_message or 'no result'}"
        )

    def cancel(self, job_id: str) -> DurableJobSnapshot:
        """Persist cancellation and signal a running handler cooperatively."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status FROM runtime_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if row is None:
                connection.execute("ROLLBACK")
                raise KeyError(f"durable job not found: {job_id}")
            status = JobStatus(row[0])
            if not status.terminal:
                terminal_status = (
                    "cancelled" if status is JobStatus.QUEUED else status.value
                )
                finished_at = _now() if status is JobStatus.QUEUED else None
                connection.execute(
                    """
                    UPDATE runtime_jobs
                    SET cancel_requested = 1, status = ?,
                        finished_at = COALESCE(?, finished_at),
                        error_type = COALESCE(?, error_type),
                        error_message = COALESCE(?, error_message)
                    WHERE job_id = ?
                    """,
                    (
                        terminal_status,
                        finished_at,
                        (
                            DurableJobCancelled.__name__
                            if status is JobStatus.QUEUED
                            else None
                        ),
                        (
                            "durable job was cancelled before execution"
                            if status is JobStatus.QUEUED
                            else None
                        ),
                        job_id,
                    ),
                )
            connection.execute("COMMIT")
        self._notify()
        return self.status(job_id)

    def wait(
        self, job_id: str, *, timeout_seconds: float | None = None
    ) -> DurableJobSnapshot:
        """Wait on worker notifications rather than repeatedly querying on a timer."""
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("durable job wait timeout must be positive")
        with self._condition:
            completed = self._condition.wait_for(
                lambda: self.status(job_id).status.terminal,
                timeout=timeout_seconds,
            )
        if not completed:
            raise TimeoutError(f"durable job wait timed out: {job_id}")
        return self.status(job_id)

    def close(self) -> None:
        """Stop accepting work and release worker resources."""
        with self._condition:
            if self._closed:
                return
            self._closed = True
        self._executor.shutdown(wait=True, cancel_futures=False)

    def __enter__(self) -> DurableJobManager:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            existing = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'runtime_jobs'"
            ).fetchone()
            if existing is None:
                connection.execute(self._table_sql())
                return
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(runtime_jobs)"
                ).fetchall()
            }
            if {"deadline_at", "timeout_seconds"}.issubset(columns) and (
                "timed_out" in str(existing[0])
            ):
                return
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("ALTER TABLE runtime_jobs RENAME TO runtime_jobs_legacy")
            connection.execute(self._table_sql())
            connection.execute(
                """
                INSERT INTO runtime_jobs (
                    job_id, kind, idempotency_key, request_sha256, payload_json,
                    status, cancel_requested, attempt_count, submitted_at,
                    started_at, finished_at, deadline_at, timeout_seconds,
                    result_json, error_type, error_message
                )
                SELECT job_id, kind, idempotency_key, request_sha256, payload_json,
                       status, cancel_requested, attempt_count, submitted_at,
                       started_at, finished_at, NULL, NULL, result_json,
                       error_type, error_message
                FROM runtime_jobs_legacy
                """
            )
            connection.execute("DROP TABLE runtime_jobs_legacy")
            connection.execute("COMMIT")

    @staticmethod
    def _table_sql() -> str:
        return """
            CREATE TABLE runtime_jobs (
                job_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL CHECK (kind IN ('run', 'replay')),
                idempotency_key TEXT NOT NULL UNIQUE,
                request_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN (
                        'queued', 'running', 'succeeded', 'failed',
                        'cancelled', 'timed_out'
                    )
                ),
                cancel_requested INTEGER NOT NULL CHECK (cancel_requested IN (0, 1)),
                attempt_count INTEGER NOT NULL,
                submitted_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                deadline_at TEXT,
                timeout_seconds REAL,
                result_json TEXT,
                error_type TEXT,
                error_message TEXT
            )
        """

    def _recover_interrupted_jobs(self) -> None:
        now = _now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                UPDATE runtime_jobs SET
                    status = CASE
                        WHEN cancel_requested = 1 THEN 'cancelled'
                        WHEN deadline_at IS NOT NULL AND deadline_at <= ? THEN 'timed_out'
                        ELSE 'queued'
                    END,
                    finished_at = CASE
                        WHEN cancel_requested = 1 THEN ?
                        WHEN deadline_at IS NOT NULL AND deadline_at <= ? THEN ?
                        ELSE NULL
                    END,
                    started_at = NULL,
                    error_type = CASE
                        WHEN cancel_requested = 1 THEN ?
                        WHEN deadline_at IS NOT NULL AND deadline_at <= ? THEN ?
                        ELSE error_type
                    END,
                    error_message = CASE
                        WHEN cancel_requested = 1 THEN 'durable job was cancelled'
                        WHEN deadline_at IS NOT NULL AND deadline_at <= ?
                            THEN 'durable job deadline expired during interruption'
                        ELSE error_message
                    END
                WHERE status = 'running'
                """,
                (
                    now,
                    now,
                    now,
                    now,
                    DurableJobCancelled.__name__,
                    now,
                    DurableJobTimedOut.__name__,
                    now,
                ),
            )
            connection.execute(
                """
                UPDATE runtime_jobs
                SET status = 'timed_out', finished_at = ?,
                    error_type = ?,
                    error_message = 'durable job deadline expired before execution'
                WHERE status = 'queued' AND deadline_at IS NOT NULL
                      AND deadline_at <= ?
                """,
                (now, DurableJobTimedOut.__name__, now),
            )
            job_ids = [
                row[0]
                for row in connection.execute(
                    "SELECT job_id FROM runtime_jobs WHERE status = 'queued' ORDER BY submitted_at, job_id"
                ).fetchall()
            ]
            connection.execute("COMMIT")
        for job_id in job_ids:
            self._schedule(job_id)

    def _schedule(self, job_id: str) -> None:
        with self._condition:
            if self._closed or job_id in self._scheduled:
                return
            self._scheduled.add(job_id)
        self._executor.submit(self._execute, job_id)

    def _execute(self, job_id: str) -> None:
        try:
            request = self._claim(job_id)
            if request is None:
                return
            handler = self._handlers[request.kind]
            try:
                result = dict(handler(request, lambda: self._stop_requested(job_id)))
                canonical_json_bytes(result)
            except Exception as exc:
                self._finish_failed(job_id, exc)
            else:
                self._finish_success(job_id, result)
        finally:
            with self._condition:
                self._scheduled.discard(job_id)
                self._condition.notify_all()

    def _claim(self, job_id: str) -> DurableJobRequest | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT kind, idempotency_key, payload_json, status,
                       cancel_requested, timeout_seconds, deadline_at
                FROM runtime_jobs WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
            if row is None or row[3] != JobStatus.QUEUED.value or bool(row[4]):
                connection.execute("COMMIT")
                return None
            if row[6] is not None and row[6] <= _now():
                connection.execute(
                    """
                    UPDATE runtime_jobs
                    SET status = 'timed_out', finished_at = ?, error_type = ?,
                        error_message = 'durable job deadline expired before execution'
                    WHERE job_id = ? AND status = 'queued'
                    """,
                    (_now(), DurableJobTimedOut.__name__, job_id),
                )
                connection.execute("COMMIT")
                return None
            connection.execute(
                """
                UPDATE runtime_jobs
                SET status = 'running', started_at = ?, attempt_count = attempt_count + 1
                WHERE job_id = ? AND status = 'queued'
                """,
                (_now(), job_id),
            )
            connection.execute("COMMIT")
        return DurableJobRequest(
            JobKind(row[0]),
            row[1],
            json.loads(row[2]),
            row[5],
        )

    def _finish_success(self, job_id: str, result: dict[str, object]) -> None:
        result_json = json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        finished_at = _now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cancellation = connection.execute(
                """
                SELECT cancel_requested, deadline_at
                FROM runtime_jobs WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
            cancelled = bool(cancellation[0])
            timed_out = cancellation[1] is not None and cancellation[1] <= finished_at
            status = (
                JobStatus.CANCELLED
                if cancelled
                else JobStatus.TIMED_OUT
                if timed_out
                else JobStatus.SUCCEEDED
            )
            connection.execute(
                """
                UPDATE runtime_jobs SET
                    status = ?, result_json = ?, finished_at = ?,
                    error_type = ?, error_message = ?
                WHERE job_id = ? AND status = 'running'
                """,
                (
                    status.value,
                    result_json,
                    finished_at,
                    (
                        DurableJobCancelled.__name__
                        if cancelled
                        else DurableJobTimedOut.__name__
                        if timed_out
                        else None
                    ),
                    (
                        "durable job was cancelled after partial evidence"
                        if cancelled
                        else (
                            "durable job deadline exceeded after partial evidence"
                            if timed_out
                            else None
                        )
                    ),
                    job_id,
                ),
            )
            connection.execute("COMMIT")

    def _finish_failed(self, job_id: str, error: Exception) -> None:
        finished_at = _now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cancellation = connection.execute(
                """
                SELECT cancel_requested, deadline_at
                FROM runtime_jobs WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
            cancelled = bool(cancellation[0])
            timed_out = cancellation[1] is not None and cancellation[1] <= finished_at
            status = (
                JobStatus.CANCELLED
                if cancelled
                else JobStatus.TIMED_OUT
                if timed_out
                else JobStatus.FAILED
            )
            connection.execute(
                """
                UPDATE runtime_jobs
                SET status = ?, error_type = ?, error_message = ?, finished_at = ?
                WHERE job_id = ? AND status = 'running'
                """,
                (
                    status.value,
                    (
                        DurableJobCancelled.__name__
                        if cancelled
                        else (
                            DurableJobTimedOut.__name__
                            if timed_out
                            else type(error).__name__
                        )
                    ),
                    (
                        "durable job was cancelled"
                        if cancelled
                        else (
                            "durable job deadline was exceeded"
                            if timed_out
                            else str(error)
                        )
                    ),
                    finished_at,
                    job_id,
                ),
            )
            connection.execute("COMMIT")

    def _stop_requested(self, job_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT cancel_requested, deadline_at
                FROM runtime_jobs WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
        return row is None or bool(row[0]) or (row[1] is not None and row[1] <= _now())

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0)
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _ensure_open(self) -> None:
        with self._condition:
            if self._closed:
                raise DurableJobError("durable job manager is closed")

    def _notify(self) -> None:
        with self._condition:
            self._condition.notify_all()


__all__ = [
    "DurableJobCancelled",
    "DurableJobError",
    "DurableJobHandler",
    "DurableJobManager",
    "DurableJobRequest",
    "DurableJobSnapshot",
    "DurableJobTimedOut",
    "JobKind",
    "JobStatus",
]
