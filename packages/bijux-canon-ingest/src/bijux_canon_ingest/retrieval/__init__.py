# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Retrieval backends, contracts, and domain types for bijux-canon-ingest."""

from __future__ import annotations

from .domain import (
    Chunk,
    ChunkId,
    ChunkMetadata,
    ChunkMetadataV1,
    ChunkText,
    Embedding,
    OBatch,
    assemble,
    from_optimized_batch,
    map_metadata_checked,
    process_batch_hybrid,
    to_optimized_batch,
    try_set_embedding,
    upcast_metadata_v1,
)
from .embedders import HashEmbedder, SentenceTransformersEmbedder
from .generators import ExtractiveGenerator
from .indexes import (
    BM25Index,
    NumpyCosineIndex,
    build_bm25_index,
    build_numpy_cosine_index,
    load_index,
)
from .ports import (
    Answer,
    Candidate,
    Citation,
    Embedder,
    Generator,
    Index,
    Indexer,
    Reranker,
)
from .rerankers import LexicalOverlapReranker

__all__ = [
    "Answer",
    "Candidate",
    "Citation",
    "Embedder",
    "Generator",
    "Index",
    "Indexer",
    "Reranker",
    "HashEmbedder",
    "SentenceTransformersEmbedder",
    "BM25Index",
    "NumpyCosineIndex",
    "build_bm25_index",
    "build_numpy_cosine_index",
    "load_index",
    "ExtractiveGenerator",
    "LexicalOverlapReranker",
    "ChunkId",
    "ChunkText",
    "ChunkMetadata",
    "Embedding",
    "Chunk",
    "assemble",
    "try_set_embedding",
    "map_metadata_checked",
    "ChunkMetadataV1",
    "upcast_metadata_v1",
    "OBatch",
    "to_optimized_batch",
    "from_optimized_batch",
    "process_batch_hybrid",
]
