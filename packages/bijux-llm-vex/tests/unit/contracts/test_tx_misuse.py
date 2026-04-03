# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import pytest

from bijux_vex.core.errors import AtomicityViolationError
from bijux_vex.infra.adapters.memory.backend import memory_backend
from bijux_vex.infra.adapters.sqlite.backend import sqlite_backend


@pytest.fixture(params=["memory", "sqlite"])
def backend(request, tmp_path):
    if request.param == "memory":
        return memory_backend()
    return sqlite_backend(tmp_path / "tx.sqlite")


def test_nested_tx_fails(backend):
    with pytest.raises(AtomicityViolationError):
        with backend.tx_factory():
            with backend.tx_factory():
                pass


def test_commit_without_enter_fails(backend):
    tx = backend.tx_factory()
    with pytest.raises(AtomicityViolationError):
        tx.commit()


def test_double_commit_and_abort_after_commit(backend):
    tx = backend.tx_factory()
    tx.__enter__()
    tx.commit()
    with pytest.raises(AtomicityViolationError):
        tx.commit()
    tx2 = backend.tx_factory()
    tx2.__enter__()
    tx2.commit()
    with pytest.raises(AtomicityViolationError):
        tx2.abort()
