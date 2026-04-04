# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""FastAPI adapter exposing chunking and RAG endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.openapi.utils import get_openapi

from bijux_canon_ingest.application.service import (
    IndexBackend,
    IngestService,
    StoredIndex,
)
from bijux_canon_ingest.processing.stages import (
    ChunkAndEmbedConfig,
    chunk_and_embed_docs,
)
from bijux_canon_ingest.interfaces.http.mappers import (
    ask_response_from_payload,
    chunk_response_from_result,
    index_build_response,
    raw_docs_from_http_docs,
    retrieve_response_from_candidates,
)
from bijux_canon_ingest.interfaces.http.models import (
    AskRequest,
    AskResponse,
    ChunkRequest,
    ChunkResponse,
    IndexBuildRequest,
    IndexBuildResponse,
    RetrieveRequest,
    RetrieveResponse,
)
from bijux_canon_ingest.result.types import Err


# Helpers


def _backend_from_str(s: str) -> IndexBackend:
    # Schema enforces allowed values; keep mapping tight and explicit.
    if s == "bm25":
        return IndexBackend.BM25
    return IndexBackend.NUMPY_COSINE


# App factory


def create_app() -> FastAPI:
    """Construct a FastAPI app with chunking and RAG endpoints."""

    app = FastAPI(title="bijux-canon-ingest", openapi_version="3.1.0")
    router = APIRouter(prefix="/v1")

    rag_app = IngestService()
    index_store: dict[str, StoredIndex] = {}

    @router.get("/healthz")
    async def healthz() -> dict[str, bool]:
        return {"ok": True}

    @router.post("/chunks", response_model=ChunkResponse)
    async def chunks(req: ChunkRequest) -> ChunkResponse:
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

        return chunk_response_from_result(res.value)

    @router.post("/index/build", response_model=IndexBuildResponse)
    async def index_build(req: IndexBuildRequest) -> IndexBuildResponse:
        docs = raw_docs_from_http_docs(req.docs)
        res = rag_app.build_index(
            docs=docs,
            backend=_backend_from_str(req.backend),
            chunk_size=req.chunk_size,
            overlap=req.overlap,
        )
        if isinstance(res, Err):
            raise HTTPException(status_code=400, detail=res.error)

        idx = res.value
        index_id = f"idx_{idx.fingerprint}"
        index_store[index_id] = idx

        return index_build_response(
            index_id,
            fingerprint=idx.fingerprint,
            schema_version=idx.schema_version,
        )

    @router.post("/retrieve", response_model=RetrieveResponse)
    async def retrieve(req: RetrieveRequest) -> RetrieveResponse:
        idx = index_store.get(req.index_id)
        if idx is None:
            raise HTTPException(status_code=404, detail="Unknown index_id")

        res = rag_app.retrieve(
            index=idx, query=req.query, top_k=req.top_k, filters=req.filters
        )
        if isinstance(res, Err):
            raise HTTPException(status_code=400, detail=res.error)

        return retrieve_response_from_candidates(res.value)

    @router.post("/ask", response_model=AskResponse)
    async def ask(req: AskRequest) -> AskResponse:
        idx = index_store.get(req.index_id)
        if idx is None:
            raise HTTPException(status_code=404, detail="Unknown index_id")

        res = rag_app.ask(
            index=idx,
            query=req.query,
            top_k=req.top_k,
            filters=req.filters,
            rerank=req.rerank,
        )
        if isinstance(res, Err):
            raise HTTPException(status_code=400, detail=res.error)

        return ask_response_from_payload(res.value)

    app.include_router(router)

    def _custom_openapi() -> dict[str, Any]:
        existing_schema = app.openapi_schema
        if isinstance(existing_schema, dict):
            return existing_schema
        app.openapi_schema = get_openapi(
            title=app.title,
            version="0.1.0",
            routes=app.routes,
            openapi_version="3.1.0",
            description=app.description,
        )
        generated_schema = app.openapi_schema
        if not isinstance(
            generated_schema, dict
        ):  # pragma: no cover - FastAPI contract
            raise RuntimeError("FastAPI returned a non-dict OpenAPI schema")
        return generated_schema

    setattr(app, "openapi", _custom_openapi)
    return app


# Ready-to-use app instance for ASGI servers.
app = create_app()
