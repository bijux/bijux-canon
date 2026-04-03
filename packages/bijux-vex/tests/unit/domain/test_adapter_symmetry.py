# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.infra.adapters.memory.backend import memory_backend
from bijux_vex.infra.adapters.hnsw.backend import hnsw_backend
from bijux_vex.infra.adapters.pgvector.backend import pgvector_backend
from bijux_vex.infra.adapters.sqlite.backend import sqlite_backend


def _public_methods(obj):
    return {m for m in dir(obj) if not m.startswith("_")}


def test_vector_source_symmetry():
    mem = memory_backend().stores.vectors
    sqlite = sqlite_backend().stores.vectors
    hnsw = hnsw_backend().stores.vectors
    backends = [mem, sqlite, hnsw]
    try:
        backends.append(pgvector_backend().stores.vectors)
    except NotImplementedError:
        # pgvector is excluded from v1 freeze; symmetry applies to active backends only
        pass
    expected = _public_methods(mem)
    for backend in backends:
        assert _public_methods(backend) == expected


def test_ledger_symmetry():
    mem = memory_backend().stores.ledger
    sqlite = sqlite_backend().stores.ledger
    hnsw = hnsw_backend().stores.ledger
    backends = [mem, sqlite, hnsw]
    try:
        backends.append(pgvector_backend().stores.ledger)
    except NotImplementedError:
        pass
    expected = _public_methods(mem)
    for backend in backends:
        assert _public_methods(backend) == expected
