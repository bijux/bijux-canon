# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from fastapi import FastAPI

from bijux_canon_index.api.v1.mutation_routes import register_mutation_routes
from bijux_canon_index.api.v1.query_routes import register_query_routes
from bijux_canon_index.api.v1.read_routes import register_read_routes


def build_app() -> FastAPI:
    app = FastAPI(title="bijux-canon-index execution API", version="v1")
    register_read_routes(app)
    register_mutation_routes(app)
    register_query_routes(app)
    return app


app = build_app()

__all__ = ["build_app", "app"]
