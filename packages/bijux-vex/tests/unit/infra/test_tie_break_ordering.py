# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.types import Chunk, Document, ExecutionRequest, Vector
from bijux_vex.infra.adapters.memory.backend import memory_backend
from bijux_vex.infra.adapters.vectorstore_registry import (
    VectorStoreDescriptor,
    VectorStoreResolution,
)
from bijux_vex.infra.adapters.vectorstore_source import VectorStoreVectorSource


class _TieAdapter:
    is_noop = False

    def insert(self, vectors, metadata=None):  # pragma: no cover - unused
        return []

    def query(self, vector, k, mode):
        return [("vec-2", 0.0), ("vec-1", 0.0)]

    def delete(self, ids):  # pragma: no cover - unused
        return 0


def test_tie_breaker_ordering_is_stable() -> None:
    backend = memory_backend()
    stores = backend.stores
    with backend.tx_factory() as tx:
        doc = Document(document_id="doc-1", text="hello")
        stores.vectors.put_document(tx, doc)
        chunk = Chunk(
            chunk_id="chunk-1", document_id=doc.document_id, text="hello", ordinal=0
        )
        stores.vectors.put_chunk(tx, chunk)
        vec1 = Vector(
            vector_id="vec-1",
            chunk_id=chunk.chunk_id,
            values=(0.0, 0.0),
            dimension=2,
            model=None,
        )
        vec2 = Vector(
            vector_id="vec-2",
            chunk_id=chunk.chunk_id,
            values=(0.0, 0.0),
            dimension=2,
            model=None,
        )
        stores.vectors.put_vector(tx, vec1)
        stores.vectors.put_vector(tx, vec2)

    descriptor = VectorStoreDescriptor(
        name="stub",
        available=True,
        supports_exact=True,
        supports_ann=False,
        delete_supported=True,
        filtering_supported=False,
        deterministic_exact=True,
        experimental=True,
        consistency=None,
        notes=None,
        version=None,
    )
    resolution = VectorStoreResolution(
        descriptor=descriptor, adapter=_TieAdapter(), uri_redacted=None
    )
    source = VectorStoreVectorSource(stores.vectors, resolution)
    request = ExecutionRequest(
        request_id="req-1",
        text=None,
        vector=(0.0, 0.0),
        top_k=2,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
        execution_mode=ExecutionMode.STRICT,
    )
    results = list(source.query("art-1", request))
    assert [res.vector_id for res in results] == ["vec-1", "vec-2"]
