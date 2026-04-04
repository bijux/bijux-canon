# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from bijux_canon_index.contracts.authz import Authz
from bijux_canon_index.contracts.resources import ExecutionResources
from bijux_canon_index.contracts.tx import Tx
from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.identity.policies import IdGenerationStrategy
from bijux_canon_index.core.types import Chunk, Document, Vector
from bijux_canon_index.infra.logging import log_event


def persist_ingest_documents(
    *,
    tx_factory: Callable[[], Tx],
    stores: ExecutionResources,
    authz: Authz,
    id_policy: IdGenerationStrategy,
    documents: list[str],
    vectors: list[list[float]],
    embedding_model: str | None,
    embedding_meta_by_index: dict[int, dict[str, str | None]],
    metadata_tuple: Callable[
        [dict[str, str | None]], tuple[tuple[str, str], ...] | None
    ],
) -> None:
    with tx_factory() as tx:
        for idx, doc_text in enumerate(documents):
            doc_id = id_policy.document_id(doc_text)
            doc = Document(document_id=doc_id, text=doc_text)
            authz.check(tx, action="put_document", resource="document")
            stores.vectors.put_document(tx, doc)
            chunk = Chunk(
                chunk_id=id_policy.chunk_id(doc.document_id, 0),
                document_id=doc.document_id,
                text=doc_text,
                ordinal=0,
            )
            authz.check(tx, action="put_chunk", resource="chunk")
            stores.vectors.put_chunk(tx, chunk)
            vec = Vector(
                vector_id=id_policy.vector_id(chunk.chunk_id, tuple(vectors[idx])),
                chunk_id=chunk.chunk_id,
                values=tuple(vectors[idx]),
                dimension=len(vectors[idx]),
                model=embedding_model,
                metadata=metadata_tuple(embedding_meta_by_index.get(idx, {}))
                if embedding_meta_by_index
                else None,
            )
            authz.check(tx, action="put_vector", resource="vector")
            stores.vectors.put_vector(tx, vec)


def invalidate_ann_artifact_if_needed(
    *,
    tx_factory: Callable[[], Tx],
    stores: ExecutionResources,
    artifact_id: str,
) -> None:
    existing_artifact = stores.ledger.get_artifact(artifact_id)
    if (
        existing_artifact
        and existing_artifact.execution_contract is ExecutionContract.NON_DETERMINISTIC
        and existing_artifact.index_state == "ready"
    ):
        updated = replace(existing_artifact, index_state="invalidated")
        with tx_factory() as tx:
            stores.ledger.put_artifact(tx, updated)
        log_event("ann_index_invalidated", artifact_id=existing_artifact.artifact_id)


__all__ = ["invalidate_ann_artifact_if_needed", "persist_ingest_documents"]
