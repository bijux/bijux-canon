# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi <bijan@bijux.io>
from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, cast

from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.execution_intent import ExecutionIntent
from bijux_canon_index.core.execution_mode import ExecutionMode
from bijux_canon_index.core.types import Chunk, Document, ExecutionRequest, Vector
from bijux_canon_index.infra.adapters.memory.backend import memory_backend
from bijux_canon_index.infra.adapters.vectorstore_registry import (
    VectorStoreDescriptor,
    VectorStoreResolution,
)
from bijux_canon_index.infra.adapters.vectorstore_source import VectorStoreVectorSource


class _TieAdapter:
    is_noop = False

    def connect(self) -> None:
        return None

    def insert(
        self,
        vectors: Iterable[Sequence[float]],
        metadata: Iterable[dict[str, Any]] | None = None,
    ) -> list[str]:  # pragma: no cover - unused
        del vectors, metadata
        return []

    def query(
        self, vector: Sequence[float], k: int, mode: str
    ) -> list[tuple[str, float]]:
        del vector, k, mode
        return [("vec-2", 0.0), ("vec-1", 0.0)]

    def delete(self, ids: Iterable[str]) -> int:  # pragma: no cover - unused
        del ids
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
        descriptor=descriptor,
        adapter=cast(Any, _TieAdapter()),
        uri_redacted=None,
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
