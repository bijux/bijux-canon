# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Filesystem lock helpers for the DuckDB execution store."""

from __future__ import annotations

import os
from pathlib import Path


def acquire_execution_store_lock(path: Path) -> int:
    """Acquire the single-writer execution-store lock file."""
    payload = f"{os.getpid()}\n".encode("ascii")
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        os.write(fd, payload)
        return fd
    except FileExistsError:
        pass

    try:
        existing = path.read_text(encoding="ascii").strip()
        existing_pid = int(existing) if existing else None
    except Exception:
        existing_pid = None

    if existing_pid == os.getpid():
        return os.open(path, os.O_RDWR)

    if existing_pid is not None:
        try:
            os.kill(existing_pid, 0)
        except OSError:
            path.unlink(missing_ok=True)
            return acquire_execution_store_lock(path)

    raise RuntimeError("execution store lock already held")


__all__ = ["acquire_execution_store_lock"]
