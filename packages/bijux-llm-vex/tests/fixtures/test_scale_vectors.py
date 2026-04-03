# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import random

from bijux_vex.core.types import Chunk, Document, Vector
from bijux_vex.infra.adapters.memory.backend import memory_backend


def build_scale_backend(count: int = 10000, dim: int = 8):
    backend = memory_backend()
    with backend.tx_factory() as tx:
        doc = Document(document_id="scale-doc", text="dense")
        backend.stores.vectors.put_document(tx, doc)
        for i in range(count):
            chunk = Chunk(
                chunk_id=f"chunk-{i}",
                document_id=doc.document_id,
                text="dense",
                ordinal=i,
            )
            backend.stores.vectors.put_chunk(tx, chunk)
            vec = tuple(random.random() for _ in range(dim))
            backend.stores.vectors.put_vector(
                tx,
                Vector(
                    vector_id=f"v-{i}",
                    chunk_id=chunk.chunk_id,
                    values=vec,
                    dimension=dim,
                ),
            )
    return backend
