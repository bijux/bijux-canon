# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Document coercion and chunk materialization helpers for indexing workflows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from bijux_canon_ingest.core.types import Chunk, RagEnv, RawDoc
from bijux_canon_ingest.processing.stages import clean_doc, iter_chunk_doc
from bijux_canon_ingest.result.types import Err, Ok, Result


def coerce_raw_doc(obj: object) -> RawDoc:
    """Accept ``RawDoc``, mappings, and tuple-like rows at package boundaries."""

    if isinstance(obj, RawDoc):
        return obj
    if isinstance(obj, Mapping):
        return RawDoc(
            doc_id=str(obj.get("doc_id", "")),
            title=str(obj.get("title", "")),
            abstract=str(obj.get("abstract", obj.get("text", ""))),
            categories=str(obj.get("categories", obj.get("category", ""))),
        )
    if isinstance(obj, (list, tuple)):
        doc_id = obj[0] if len(obj) >= 1 else ""
        text = obj[1] if len(obj) >= 2 else ""
        title = obj[2] if len(obj) >= 3 else ""
        category = obj[3] if len(obj) >= 4 else ""
        return RawDoc(
            doc_id=str(doc_id),
            title=str(title or ""),
            abstract=str(text or ""),
            categories=str(category or ""),
        )
    raise TypeError("docs must be RawDoc, mapping, or tuple/list")


def raw_docs_to_chunks(
    docs: Iterable[object],
    *,
    chunk_size: int,
    overlap: int,
    tail_policy: str,
) -> Result[list[Chunk], str]:
    env = RagEnv(chunk_size=chunk_size, overlap=overlap, tail_policy=tail_policy)
    chunks: list[Chunk] = []
    for doc in docs:
        raw = coerce_raw_doc(doc)
        cleaned = clean_doc(raw)
        for index, chunk in enumerate(iter_chunk_doc(cleaned, env)):
            created = Chunk.create(
                doc_id=raw.doc_id,
                chunk_index=index,
                start=chunk.start,
                end=chunk.end,
                text=chunk.text,
                title=raw.title,
                category=raw.categories,
                embedding=(),
                metadata={"title": raw.title, "category": raw.categories},
            )
            if isinstance(created, Err):
                return Err(created.error)
            chunks.append(created.value)
    return Ok(chunks)


__all__ = ["coerce_raw_doc", "raw_docs_to_chunks"]
