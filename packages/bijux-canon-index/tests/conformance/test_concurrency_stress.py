# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor

from bijux_vex.infra.adapters.memory.backend import memory_backend
from bijux_vex.core.types import Document


def _write_doc(name: str) -> str:
    backend = memory_backend()
    with backend.tx_factory() as tx:
        backend.stores.vectors.put_document(tx, Document(document_id=name, text=name))
    return name


def test_parallel_backends_do_not_leak_state():
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(_write_doc, ["a", "b"]))
    assert sorted(results) == ["a", "b"]
