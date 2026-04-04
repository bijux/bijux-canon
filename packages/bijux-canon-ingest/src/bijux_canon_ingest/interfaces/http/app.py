# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""FastAPI adapter exposing chunking and RAG endpoints."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, HTTPException

from bijux_canon_ingest.application.service import (
    IngestService,
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
from bijux_canon_ingest.interfaces.http.runtime import (
    InMemoryIndexStore,
    build_openapi_factory,
    index_backend_from_name,
)
from bijux_canon_ingest.result.types import Err


def create_app() -> FastAPI:
    """Construct a FastAPI app with chunking and RAG endpoints."""

    app = FastAPI(title="bijux-canon-ingest", openapi_version="3.1.0")
    router = APIRouter(prefix="/v1")

    rag_app = IngestService()
    index_store = InMemoryIndexStore()

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
            backend=index_backend_from_name(req.backend),
            chunk_size=req.chunk_size,
            overlap=req.overlap,
        )
        if isinstance(res, Err):
            raise HTTPException(status_code=400, detail=res.error)

        idx = res.value
        index_id = index_store.put(idx)

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
    setattr(app, "openapi", build_openapi_factory(app))
    return app


# Ready-to-use app instance for ASGI servers.
app = create_app()
