# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Bounded process leases for DuckDB execution stores."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import errno
import fcntl
import json
import os
from pathlib import Path
import threading
import time
from uuid import uuid4


class ExecutionStoreLockTimeout(TimeoutError):
    """Raised when a store lease cannot be acquired within its wait budget."""


class ExecutionStoreLockUpgradeError(RuntimeError):
    """Raised when local readers prevent a safe shared-to-exclusive upgrade."""


@dataclass(slots=True)
class _HeldLease:
    fd: int
    exclusive: bool
    pid: int
    references: int
    token: str


_PROCESS_LEASES: dict[Path, _HeldLease] = {}
_PROCESS_LEASES_LOCK = threading.RLock()


def _reset_leases_after_fork() -> None:
    for held in _PROCESS_LEASES.values():
        try:
            os.close(held.fd)
        except OSError:
            pass
    _PROCESS_LEASES.clear()


os.register_at_fork(after_in_child=_reset_leases_after_fork)


class ExecutionStoreLease:
    """One reference to a process-scoped shared or exclusive file lease."""

    def __init__(self, *, path: Path, held: _HeldLease) -> None:
        self.path = path
        self.exclusive = held.exclusive
        self.token = held.token
        self._released = False

    def release(self) -> None:
        """Release this reference and the kernel lease after its final owner."""
        if self._released:
            return
        with _PROCESS_LEASES_LOCK:
            held = _PROCESS_LEASES.get(self.path)
            if held is None or held.token != self.token:
                self._released = True
                return
            held.references -= 1
            if held.references == 0:
                try:
                    if held.exclusive:
                        _write_record(
                            held.fd,
                            {
                                "pid": os.getpid(),
                                "released_at": datetime.now(tz=UTC).isoformat(),
                                "state": "released",
                                "token": held.token,
                            },
                        )
                finally:
                    fcntl.flock(held.fd, fcntl.LOCK_UN)
                    os.close(held.fd)
                    del _PROCESS_LEASES[self.path]
            self._released = True

    def __enter__(self) -> ExecutionStoreLease:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.release()


def acquire_execution_store_lease(
    path: Path,
    *,
    exclusive: bool,
    timeout_seconds: float = 5.0,
    poll_interval_seconds: float = 0.01,
) -> ExecutionStoreLease:
    """Acquire a reentrant process lease with an explicit bounded wait."""
    if timeout_seconds < 0:
        raise ValueError("lock timeout must be non-negative")
    if poll_interval_seconds <= 0:
        raise ValueError("lock poll interval must be positive")
    resolved = path.resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with _PROCESS_LEASES_LOCK:
        existing = _PROCESS_LEASES.get(resolved)
        if existing is not None:
            if exclusive and not existing.exclusive:
                raise ExecutionStoreLockUpgradeError(
                    "cannot acquire a writer lease while this process holds readers"
                )
            existing.references += 1
            return ExecutionStoreLease(path=resolved, held=existing)

        fd = os.open(resolved, os.O_CREAT | os.O_RDWR, 0o600)
        operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                fcntl.flock(fd, operation | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in {errno.EACCES, errno.EAGAIN}:
                    os.close(fd)
                    raise
                if time.monotonic() >= deadline:
                    owner = _read_record(resolved)
                    os.close(fd)
                    detail = f"; last owner={owner}" if owner is not None else ""
                    raise ExecutionStoreLockTimeout(
                        f"execution store lock wait exceeded {timeout_seconds:.3f}s"
                        f"{detail}"
                    ) from exc
                remaining = max(0.0, deadline - time.monotonic())
                time.sleep(min(poll_interval_seconds, remaining))

        token = uuid4().hex
        held = _HeldLease(
            fd=fd,
            exclusive=exclusive,
            pid=os.getpid(),
            references=1,
            token=token,
        )
        _PROCESS_LEASES[resolved] = held
        if exclusive:
            previous = _read_record(resolved)
            recovered_stale_owner = _record_is_stale(previous)
            _write_record(
                fd,
                {
                    "acquired_at": datetime.now(tz=UTC).isoformat(),
                    "mode": "exclusive",
                    "pid": os.getpid(),
                    "recovered_stale_owner": recovered_stale_owner,
                    "state": "acquired",
                    "token": token,
                },
            )
        return ExecutionStoreLease(path=resolved, held=held)


def acquire_execution_store_lock(
    path: Path,
    *,
    timeout_seconds: float = 5.0,
) -> ExecutionStoreLease:
    """Acquire the exclusive execution-store lease used by writers."""
    return acquire_execution_store_lease(
        path,
        exclusive=True,
        timeout_seconds=timeout_seconds,
    )


def _read_record(path: Path) -> dict[str, object] | None:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return record if isinstance(record, dict) else None


def _record_is_stale(record: dict[str, object] | None) -> bool:
    if record is None:
        return False
    # Holding the new exclusive kernel lease proves any earlier acquisition
    # record no longer owns the coordination inode, even if its PID was reused.
    return record.get("state") == "acquired"


def _write_record(fd: int, record: dict[str, object]) -> None:
    payload = (
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    os.lseek(fd, 0, os.SEEK_SET)
    os.ftruncate(fd, 0)
    os.write(fd, payload)
    os.fsync(fd)


__all__ = [
    "ExecutionStoreLease",
    "ExecutionStoreLockTimeout",
    "ExecutionStoreLockUpgradeError",
    "acquire_execution_store_lease",
    "acquire_execution_store_lock",
]
