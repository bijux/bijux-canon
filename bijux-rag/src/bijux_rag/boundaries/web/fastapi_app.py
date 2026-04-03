# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""FastAPI adapter exposing chunking and RAG endpoints.

# pyright: reportUnusedFunction=false
"""

from __future__ import annotations

from typing import Any, Dict, cast

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field, model_validator

from bijux_rag.core.rag_types import RawDoc
from bijux_rag.rag.app import IndexBackend, RagApp, RagIndex
from bijux_rag.rag.ports import Answer, Candidate
from bijux_rag.rag.stages import ChunkAndEmbedConfig, chunk_and_embed_docs
from bijux_rag.result.types import Err

# API Models (request/response)


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


class PChunkResponse(BaseModel):
    chunks: list[ChunkOut]


class PChunkRequest(BaseModel):
    chunk_size: int = Field(128, ge=1)
    overlap: int = Field(0, ge=0)
    include_embeddings: bool = True
    docs: list[DocIn] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _validate_overlap(self) -> "PChunkRequest":
        if self.overlap >= self.chunk_size:
            raise ValueError("overlap must be < chunk_size")
        return self


class IndexBuildRequest(BaseModel):
    docs: list[DocIn] = Field(..., min_length=1)
    backend: str = Field(..., pattern="^(bm25|numpy-cosine)$")
    chunk_size: int = Field(512, ge=1)
    overlap: int = Field(50, ge=0)

    @model_validator(mode="after")
    def _validate_overlap(self) -> "IndexBuildRequest":
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


class PCandidate(BaseModel):
    score: float
    chunk: Any
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrieveResponse(BaseModel):
    candidates: list[PCandidate]


class AskRequest(BaseModel):
    index_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1)
    rerank: bool = True
    filters: dict[str, str] = Field(default_factory=dict)


class PCitation(BaseModel):
    doc_id: str
    chunk_id: str
    start: int
    end: int
    text: str | None = None


class AskResponse(BaseModel):
    answer: str
    citations: list[PCitation]
    candidates: list[PCandidate]


# Helpers


def _backend_from_str(s: str) -> IndexBackend:
    # Schema enforces allowed values; keep mapping tight and explicit.
    if s == "bm25":
        return IndexBackend.BM25
    return IndexBackend.NUMPY_COSINE


# App factory


def create_app() -> FastAPI:
    """Construct a FastAPI app with chunking and RAG endpoints."""

    app = FastAPI(title="bijux-rag", openapi_version="3.1.0")
    router = APIRouter(prefix="/v1")

    _APP = RagApp()
    _INDEX_STORE: Dict[str, RagIndex] = {}

    @router.get("/healthz")
    async def healthz() -> dict[str, bool]:
        return {"ok": True}

    @router.post("/chunks", response_model=PChunkResponse)
    async def chunks(req: PChunkRequest) -> PChunkResponse:
        # Boundary validation ensures we do not 500 on invalid inputs.
        try:
            docs = [(d.doc_id, d.text, d.title, d.category) for d in req.docs]
            cfg = ChunkAndEmbedConfig(
                chunk_size=req.chunk_size,
                overlap=req.overlap,
                include_embeddings=req.include_embeddings,
            )
            res = chunk_and_embed_docs(docs, cfg)
        except ValueError as e:
            # Defensive: should be unreachable if request validation is correct.
            raise HTTPException(status_code=422, detail=str(e)) from e

        if isinstance(res, Err):
            raise HTTPException(status_code=400, detail=res.error)

        return PChunkResponse(
            chunks=[
                ChunkOut(
                    doc_id=c.doc_id,
                    text=c.text,
                    start=c.start,
                    end=c.end,
                    metadata=dict(c.metadata),
                    embedding=c.embedding if c.embedding else None,
                    chunk_id=c.chunk_id,
                )
                for c in res.value
            ]
        )

    @router.post("/index/build", response_model=IndexBuildResponse)
    async def index_build(req: IndexBuildRequest) -> IndexBuildResponse:
        docs = [
            RawDoc(
                doc_id=d.doc_id,
                title=d.title or "",
                abstract=d.text,
                categories=d.category or "",
            )
            for d in req.docs
        ]
        res = _APP.build_index(
            docs=docs,
            backend=_backend_from_str(req.backend),
            chunk_size=req.chunk_size,
            overlap=req.overlap,
        )
        if isinstance(res, Err):
            raise HTTPException(status_code=400, detail=res.error)

        idx = res.value
        index_id = f"idx_{idx.fingerprint}"
        _INDEX_STORE[index_id] = idx

        return IndexBuildResponse(
            index_id=index_id,
            fingerprint=idx.fingerprint,
            schema_version=idx.schema_version,
        )

    @router.post("/retrieve", response_model=RetrieveResponse)
    async def retrieve(req: RetrieveRequest) -> RetrieveResponse:
        idx = _INDEX_STORE.get(req.index_id)
        if idx is None:
            raise HTTPException(status_code=404, detail="Unknown index_id")

        res = _APP.retrieve(index=idx, query=req.query, top_k=req.top_k, filters=req.filters)
        if isinstance(res, Err):
            raise HTTPException(status_code=400, detail=res.error)

        candidates: list[Candidate] = res.value
        return RetrieveResponse(
            candidates=[
                PCandidate(
                    score=c.score,
                    chunk={
                        "doc_id": c.chunk.doc_id,
                        "chunk_id": c.chunk.chunk_id,
                        "text": c.chunk.text,
                        "start": c.chunk.start,
                        "end": c.chunk.end,
                        "metadata": dict(c.chunk.metadata),
                    },
                    metadata=dict(c.metadata),
                )
                for c in candidates
            ]
        )

    @router.post("/ask", response_model=AskResponse)
    async def ask(req: AskRequest) -> AskResponse:
        idx = _INDEX_STORE.get(req.index_id)
        if idx is None:
            raise HTTPException(status_code=404, detail="Unknown index_id")

        res = _APP.ask(
            index=idx,
            query=req.query,
            top_k=req.top_k,
            filters=req.filters,
            rerank=req.rerank,
        )
        if isinstance(res, Err):
            raise HTTPException(status_code=400, detail=res.error)

        ans = cast(Answer, res.value)
        return AskResponse(
            answer=ans.text,
            citations=[
                PCitation(
                    doc_id=c.doc_id,
                    chunk_id=c.chunk_id,
                    start=c.start,
                    end=c.end,
                    text=c.text,
                )
                for c in ans.citations
            ],
            candidates=[
                PCandidate(
                    score=c.score,
                    chunk={
                        "doc_id": c.chunk.doc_id,
                        "chunk_id": c.chunk.chunk_id,
                        "text": c.chunk.text,
                        "start": c.chunk.start,
                        "end": c.chunk.end,
                        "metadata": dict(c.chunk.metadata),
                    },
                    metadata=dict(c.metadata),
                )
                for c in ans.candidates
            ],
        )

    app.include_router(router)

    def _custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        app.openapi_schema = get_openapi(
            title=app.title,
            version="0.1.0",
            routes=app.routes,
            openapi_version="3.1.0",
            description=app.description,
        )
        return app.openapi_schema

    app.openapi = _custom_openapi  # type: ignore[method-assign]
    return app


# Ready-to-use app instance for ASGI servers.
app = create_app()
