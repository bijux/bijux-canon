# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from fastapi import FastAPI

from bijux_canon_index.api.v1.mutation_routes import register_mutation_routes
from bijux_canon_index.api.v1.query_routes import register_query_routes
from bijux_canon_index.api.v1.read_routes import register_read_routes

OPENAPI_TAGS = [
    {
        "name": "Discovery",
        "description": "Read-only endpoints that describe backend capabilities and inventory.",
    },
    {
        "name": "Materialization",
        "description": "Endpoints that ingest data or materialize reusable execution artifacts.",
    },
    {
        "name": "Execution",
        "description": "Endpoints that execute queries, explain results, or replay prior outcomes.",
    },
]


def build_app() -> FastAPI:
    app = FastAPI(
        title="bijux-canon-index API",
        summary="Contract-driven vector execution and replayable retrieval.",
        description=(
            "The bijux-canon-index HTTP API exposes the v1 surface for deterministic "
            "and bounded vector execution. It separates capability discovery, artifact "
            "materialization, and query execution so operators can review the contract "
            "they are invoking before they ship it."
        ),
        version="v1",
        openapi_version="3.1.0",
        contact={"name": "Bijux", "url": "https://github.com/bijux/bijux-canon"},
        license_info={
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0",
        },
        servers=[{"url": "/"}],
        openapi_tags=OPENAPI_TAGS,
    )
    register_read_routes(app)
    register_mutation_routes(app)
    register_query_routes(app)
    return app


app = build_app()

__all__ = ["build_app", "app"]
