# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from bijux_vex.core.types import Vector
from bijux_vex.infra.adapters.metadata_migrations import CURRENT_VECTOR_METADATA_VERSION


@dataclass(frozen=True)
class VectorStoreMetadata:
    doc_id: str
    chunk_id: str
    source_uri: str | None
    created_at: str
    embedding: dict[str, str | None]
    embedding_ref: dict[str, str | None]
    tags: tuple[str, ...]


def build_vectorstore_metadata(
    *,
    vector: Vector,
    document_id: str,
    source_uri: str | None = None,
    tags: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    embedding_meta = dict(vector.metadata or ())
    embedding_ref = {
        "provider": embedding_meta.get("embedding_provider"),
        "model": vector.model,
        "version": embedding_meta.get("embedding_model_version"),
    }
    return {
        "schema_version": CURRENT_VECTOR_METADATA_VERSION,
        "doc_id": document_id,
        "chunk_id": vector.chunk_id,
        "source_uri": source_uri,
        "created_at": datetime.now(UTC).isoformat(),
        "embedding": embedding_meta,
        "embedding_ref": embedding_ref,
        "tags": list(tags or ()),
    }


__all__ = ["VectorStoreMetadata", "build_vectorstore_metadata"]
