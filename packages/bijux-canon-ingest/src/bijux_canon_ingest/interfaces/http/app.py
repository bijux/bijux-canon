# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""FastAPI adapter exposing chunking and RAG endpoints."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, HTTPException

from bijux_canon_ingest.application.service import (
    IngestService,
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
    HealthResponse,
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
from bijux_canon_ingest.processing.stages import (
    ChunkAndEmbedConfig,
    chunk_and_embed_docs,
)
from bijux_canon_ingest.result.types import Err


def create_app() -> FastAPI:
    """Construct a FastAPI app with chunking and RAG endpoints."""

    app = FastAPI(
        title="bijux-canon-ingest API",
        summary="Deterministic chunking, indexing, retrieval, and answer assembly.",
        description=(
            "The bijux-canon-ingest HTTP API exposes the v1 ingest boundary for "
            "chunk generation, index construction, retrieval, and answer synthesis. "
            "It keeps the ingestion lifecycle explicit so operators can trace what "
            "was chunked, indexed, retrieved, and answered."
        ),
        version="v1",
        openapi_version="3.1.0",
        contact={"name": "Bijux", "url": "https://github.com/bijux/bijux-canon"},
        license_info={
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0",
        },
        servers=[{"url": "/"}],
        openapi_tags=[
            {
                "name": "Chunking",
                "description": "Endpoints that split raw documents into chunk payloads.",
            },
            {
                "name": "Indexing",
                "description": "Endpoints that build and manage retrievable indexes.",
            },
            {
                "name": "Retrieval",
                "description": "Endpoints that retrieve evidence or synthesize answers.",
            },
            {
                "name": "Health",
                "description": "Operational health signals for the HTTP adapter.",
            },
        ],
    )
    router = APIRouter(prefix="/v1")

    rag_app = IngestService()
    index_store = InMemoryIndexStore()

    @router.get(
        "/healthz",
        response_model=HealthResponse,
        tags=["Health"],
        summary="Report adapter health",
        description="Return a lightweight liveness signal for the ingest HTTP adapter.",
        operation_id="getIngestHealth",
    )
    async def healthz() -> dict[str, bool]:
        return {"ok": True}

    @router.post(
        "/chunks",
        response_model=ChunkResponse,
        tags=["Chunking"],
        summary="Chunk documents",
        description=(
            "Split submitted documents into chunk payloads and optionally include "
            "embeddings for each emitted chunk."
        ),
        operation_id="chunkDocuments",
    )
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

    @router.post(
        "/index/build",
        response_model=IndexBuildResponse,
        tags=["Indexing"],
        summary="Build an index",
        description=(
            "Chunk the submitted documents, build an index using the requested backend, "
            "and return the stable identifier for later retrieval."
        ),
        operation_id="buildIndex",
    )
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

    @router.post(
        "/retrieve",
        response_model=RetrieveResponse,
        tags=["Retrieval"],
        summary="Retrieve ranked candidates",
        description=(
            "Run retrieval against a built index and return the ranked candidate chunks "
            "that satisfy the query and optional filters."
        ),
        operation_id="retrieveCandidates",
    )
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

    @router.post(
        "/ask",
        response_model=AskResponse,
        tags=["Retrieval"],
        summary="Answer a query from the index",
        description=(
            "Retrieve candidates from the selected index, optionally rerank them, and "
            "return a synthesized answer with explicit citations."
        ),
        operation_id="answerQuery",
    )
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
    app.openapi = build_openapi_factory(app)
    return app


# Ready-to-use app instance for ASGI servers.
app = create_app()
