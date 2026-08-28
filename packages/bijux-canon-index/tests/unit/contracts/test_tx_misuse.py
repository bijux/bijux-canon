# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

import pytest

from bijux_canon_index.core.errors import AtomicityViolationError
from bijux_canon_index.infra.adapters.memory.backend import (
    MemoryFixture,
    memory_backend,
)
from bijux_canon_index.infra.adapters.sqlite.backend import (
    SQLiteFixture,
    sqlite_backend,
)


@pytest.fixture(params=["memory", "sqlite"])
def backend(
    request: pytest.FixtureRequest, tmp_path: Path
) -> MemoryFixture | SQLiteFixture:
    if request.param == "memory":
        return memory_backend()
    return sqlite_backend(str(tmp_path / "tx.sqlite"))


def test_nested_tx_fails(backend: MemoryFixture | SQLiteFixture) -> None:
    with (
        pytest.raises(AtomicityViolationError),
        backend.tx_factory(),
        backend.tx_factory(),
    ):
        pass


def test_commit_without_enter_fails(backend: MemoryFixture | SQLiteFixture) -> None:
    tx = backend.tx_factory()
    with pytest.raises(AtomicityViolationError):
        tx.commit()


def test_double_commit_and_abort_after_commit(
    backend: MemoryFixture | SQLiteFixture,
) -> None:
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
