# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""HTTP request and response models for the ingest FastAPI adapter."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class DocIn(BaseModel):
    doc_id: str = Field(..., min_length=1, description="Stable document identifier.")
    text: str = Field(..., min_length=1, description="Full document text to process.")
    title: str | None = Field(
        default=None,
        description="Optional reader-facing title used for retrieval displays.",
    )
    category: str | None = Field(
        default=None,
        description="Optional category label used for filtering or grouping.",
    )


class ChunkOut(BaseModel):
    doc_id: str = Field(description="Source document identifier for the chunk.")
    text: str = Field(description="Chunk text returned by the pipeline.")
    start: int = Field(description="Inclusive character offset where the chunk starts.")
    end: int = Field(description="Exclusive character offset where the chunk ends.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Chunk metadata preserved by the ingest pipeline.",
    )
    embedding: tuple[float, ...] | None = Field(
        default=None,
        description="Optional embedding values when embeddings are requested.",
    )
    chunk_id: str | None = Field(
        default=None,
        description="Stable chunk identifier when one has been materialized.",
    )


class ChunkResponse(BaseModel):
    chunks: list[ChunkOut] = Field(
        description="Chunk sequence produced from the submitted documents."
    )


class ChunkRequest(BaseModel):
    chunk_size: int = Field(
        128,
        ge=1,
        description="Target chunk size used by the chunking stage.",
    )
    overlap: int = Field(
        0,
        ge=0,
        description="Character overlap preserved between adjacent chunks.",
    )
    include_embeddings: bool = Field(
        True,
        description="Whether chunk embeddings should be included in the response.",
    )
    docs: list[DocIn] = Field(
        ...,
        min_length=1,
        description="Documents that should be chunked by the API.",
    )

    @model_validator(mode="after")
    def validate_overlap(self) -> ChunkRequest:
        if self.overlap >= self.chunk_size:
            raise ValueError("overlap must be < chunk_size")
        return self


class IndexBuildRequest(BaseModel):
    docs: list[DocIn] = Field(
        ...,
        min_length=1,
        description="Documents that should be indexed into a retrievable store.",
    )
    backend: str = Field(
        ...,
        pattern="^(bm25|numpy-cosine)$",
        description="Retrieval backend used to build the index.",
    )
    chunk_size: int = Field(
        512,
        ge=1,
        description="Chunk size used during index construction.",
    )
    overlap: int = Field(
        50,
        ge=0,
        description="Chunk overlap preserved during index construction.",
    )

    @model_validator(mode="after")
    def validate_overlap(self) -> IndexBuildRequest:
        if self.overlap >= self.chunk_size:
            raise ValueError("overlap must be < chunk_size")
        return self


class IndexBuildResponse(BaseModel):
    index_id: str = Field(description="Stable identifier assigned to the built index.")
    fingerprint: str = Field(
        description="Fingerprint of the built index contents and configuration."
    )
    schema_version: int = Field(
        description="Schema version emitted by the index representation."
    )


class RetrieveRequest(BaseModel):
    index_id: str = Field(
        ...,
        min_length=1,
        description="Index identifier returned by the index build endpoint.",
    )
    query: str = Field(..., min_length=1, description="Reader query text.")
    top_k: int = Field(
        5,
        ge=1,
        description="Maximum number of ranked retrieval candidates to return.",
    )
    filters: dict[str, str] = Field(
        default_factory=dict,
        description="Optional metadata filters applied during retrieval.",
    )


class CandidateModel(BaseModel):
    score: float = Field(description="Score assigned to the retrieval candidate.")
    chunk: Any = Field(description="Chunk payload associated with the candidate.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Candidate metadata preserved from indexing time.",
    )


class RetrieveResponse(BaseModel):
    candidates: list[CandidateModel] = Field(
        description="Ranked retrieval candidates returned for the query."
    )


class AskRequest(BaseModel):
    index_id: str = Field(
        ...,
        min_length=1,
        description="Index identifier returned by the index build endpoint.",
    )
    query: str = Field(..., min_length=1, description="Reader query text.")
    top_k: int = Field(
        5,
        ge=1,
        description="Maximum number of retrieval candidates to use for answering.",
    )
    rerank: bool = Field(
        True,
        description="Whether the answer flow should rerank retrieved candidates.",
    )
    filters: dict[str, str] = Field(
        default_factory=dict,
        description="Optional metadata filters applied before answer synthesis.",
    )


class CitationModel(BaseModel):
    doc_id: str = Field(description="Source document identifier.")
    chunk_id: str = Field(description="Chunk identifier cited by the answer.")
    start: int = Field(description="Inclusive cited start offset.")
    end: int = Field(description="Exclusive cited end offset.")
    text: str | None = Field(
        default=None,
        description="Optional cited text span carried with the citation.",
    )


class AskResponse(BaseModel):
    answer: str = Field(description="Reader-facing answer synthesized by the API.")
    citations: list[CitationModel] = Field(
        description="Evidence citations supporting the returned answer."
    )
    candidates: list[CandidateModel] = Field(
        description="Ranked candidates that informed the answer."
    )


class HealthResponse(BaseModel):
    ok: bool = Field(description="Liveness indicator for the HTTP adapter.")


class CorpusIngestRequest(BaseModel):
    root_path: str = Field(..., min_length=1)
    root_name: str = Field(..., min_length=1)
    corpus_name: str = Field(..., min_length=1)
    include: list[str] = Field(default_factory=lambda: ["**/*"], min_length=1)
    exclude: list[str] = Field(default_factory=list)
    symlink_policy: Literal["reject", "files_within_root", "all_within_root"] = "reject"
    max_depth: int = Field(default=64, gt=0)
    max_entries: int = Field(default=100_000, gt=0)
    max_files: int = Field(default=50_000, gt=0)
    max_file_bytes: int = Field(default=64 * 1024 * 1024, gt=0)
    max_total_bytes: int = Field(default=2 * 1024 * 1024 * 1024, gt=0)
    max_seconds: float = Field(default=300.0, gt=0)
    corpus_lock_path: str | None = None
    publication_root: str | None = None


class CorpusIngestResponse(BaseModel):
    canonical_byte_length: int
    canonical_sha256: str
    chunk_count: int
    configuration_sha256: str
    corpus_lock: dict[str, Any]
    delta: dict[str, Any] | None
    discovery_issue_count: int
    disposition: Literal["initial", "unchanged", "changed"]
    document_count: int
    formats: dict[str, int]
    ocr_required_count: int
    publication: dict[str, Any] | None
    rejection_count: int
    schema_version: Literal["bijux.canon.ingest.result.v2"]
    snapshot_id: str


__all__ = [
    "AskRequest",
    "AskResponse",
    "CandidateModel",
    "ChunkOut",
    "ChunkRequest",
    "ChunkResponse",
    "CitationModel",
    "CorpusIngestRequest",
    "CorpusIngestResponse",
    "DocIn",
    "HealthResponse",
    "IndexBuildRequest",
    "IndexBuildResponse",
    "RetrieveRequest",
    "RetrieveResponse",
]
