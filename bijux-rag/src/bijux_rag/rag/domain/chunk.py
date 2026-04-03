# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG compositional domain model: assemble subsystem ADTs safely (end-of-Bijux RAG; domain-modeling)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable, TypeAlias
from uuid import UUID, uuid4

from bijux_rag.fp.error import ErrInfo, ErrorCode
from bijux_rag.fp.validation import Validation, v_failure, v_success

from .embedding import Embedding
from .metadata import ChunkMetadata
from .text import ChunkText

ChunkId: TypeAlias = UUID


@dataclass(frozen=True, slots=True)
class Chunk:
    id: ChunkId = field(default_factory=uuid4)
    text: ChunkText = field(default_factory=lambda: ChunkText(content=""))
    metadata: ChunkMetadata = field(default_factory=lambda: ChunkMetadata(source="", tags=()))
    embedding: Embedding | None = None


def assemble(
    text: ChunkText, meta: ChunkMetadata, emb: Embedding | None = None
) -> Validation[Chunk, ErrInfo]:
    errs: list[ErrInfo] = []

    norm_tags = tuple(dict.fromkeys(meta.tags))
    if norm_tags != meta.tags:
        meta = replace(meta, tags=norm_tags)

    if emb is not None:
        if meta.embedding_model is not None and meta.embedding_model != emb.model:
            errs.append(
                ErrInfo(ErrorCode.EMB_MODEL_MISMATCH, f"{emb.model} != {meta.embedding_model}")
            )
        if meta.expected_dim is not None and meta.expected_dim != emb.dim:
            errs.append(ErrInfo(ErrorCode.EMB_DIM_MISMATCH, f"{emb.dim} != {meta.expected_dim}"))

    return (
        v_failure(tuple(errs))
        if errs
        else v_success(Chunk(text=text, metadata=meta, embedding=emb))
    )


def try_set_embedding(chunk: Chunk, emb: Embedding | None) -> Validation[Chunk, ErrInfo]:
    return assemble(chunk.text, chunk.metadata, emb)


def map_metadata_checked(
    chunk: Chunk, f: Callable[[ChunkMetadata], ChunkMetadata]
) -> Validation[Chunk, ErrInfo]:
    return assemble(chunk.text, f(chunk.metadata), chunk.embedding)


@dataclass(frozen=True, slots=True)
class ChunkMetadataV1:
    source: str
    tags: list[str]


def upcast_metadata_v1(v1: ChunkMetadataV1) -> ChunkMetadata:
    return ChunkMetadata(source=v1.source, tags=tuple(v1.tags))


__all__ = [
    "ChunkId",
    "Chunk",
    "assemble",
    "try_set_embedding",
    "map_metadata_checked",
    "ChunkMetadataV1",
    "upcast_metadata_v1",
]
