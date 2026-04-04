# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""HTTP request and response models for the ingest FastAPI adapter."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class DocIn(BaseModel):
    doc_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    title: str | None = None
    category: str | None = None


class ChunkOut(BaseModel):
    doc_id: str
    text: str
    start: int
    end: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: tuple[float, ...] | None = None
    chunk_id: str | None = None


class ChunkResponse(BaseModel):
    chunks: list[ChunkOut]


class ChunkRequest(BaseModel):
    chunk_size: int = Field(128, ge=1)
    overlap: int = Field(0, ge=0)
    include_embeddings: bool = True
    docs: list[DocIn] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_overlap(self) -> ChunkRequest:
        if self.overlap >= self.chunk_size:
            raise ValueError("overlap must be < chunk_size")
        return self


class IndexBuildRequest(BaseModel):
    docs: list[DocIn] = Field(..., min_length=1)
    backend: str = Field(..., pattern="^(bm25|numpy-cosine)$")
    chunk_size: int = Field(512, ge=1)
    overlap: int = Field(50, ge=0)

    @model_validator(mode="after")
    def validate_overlap(self) -> IndexBuildRequest:
        if self.overlap >= self.chunk_size:
            raise ValueError("overlap must be < chunk_size")
        return self


class IndexBuildResponse(BaseModel):
    index_id: str
    fingerprint: str
    schema_version: int


class RetrieveRequest(BaseModel):
    index_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1)
    filters: dict[str, str] = Field(default_factory=dict)


class CandidateModel(BaseModel):
    score: float
    chunk: Any
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrieveResponse(BaseModel):
    candidates: list[CandidateModel]


class AskRequest(BaseModel):
    index_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1)
    rerank: bool = True
    filters: dict[str, str] = Field(default_factory=dict)


class CitationModel(BaseModel):
    doc_id: str
    chunk_id: str
    start: int
    end: int
    text: str | None = None


class AskResponse(BaseModel):
    answer: str
    citations: list[CitationModel]
    candidates: list[CandidateModel]


__all__ = [
    "AskRequest",
    "AskResponse",
    "CandidateModel",
    "ChunkOut",
    "ChunkRequest",
    "ChunkResponse",
    "CitationModel",
    "DocIn",
    "IndexBuildRequest",
    "IndexBuildResponse",
    "RetrieveRequest",
    "RetrieveResponse",
]
