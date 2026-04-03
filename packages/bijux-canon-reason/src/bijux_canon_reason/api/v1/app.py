# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""FastAPI application for bijux-canon-reason.

Endpoints (v1):
  POST /v1/runs           -> create+execute a run (writes artifacts)
  GET  /v1/runs/{run_id}  -> read run_meta.json
  GET  /v1/runs/{run_id}/manifest -> read manifest.json
  GET  /v1/runs/{run_id}/trace    -> stream trace.jsonl
  POST /v1/runs/{run_id}/verify   -> verify trace against plan/evidence
  POST /v1/runs/{run_id}/replay   -> replay using ReplayRuntime

  CRUD demo (persistent, deterministic):
  POST /v1/items          -> create (idempotent by name)
  GET  /v1/items          -> list (paginated)
  GET  /v1/items/{id}     -> fetch
  PUT  /v1/items/{id}     -> update
  DELETE /v1/items/{id}   -> soft delete (404 afterwards)
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import os
from pathlib import Path
from typing import no_type_check

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from bijux_canon_reason.api.v1.http_guards import (
    MAX_OFFSET,
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_ITEMS,
    enforce_response_size,
    guard_request,
    initialize_rate_limit_state,
)
from bijux_canon_reason.api.v1.item_routes import configure_item_store, register_item_routes
from bijux_canon_reason.api.v1.run_routes import register_run_routes


def create_app(*, artifacts_dir: Path | None = None) -> FastAPI:
    artifacts_dir = artifacts_dir or Path("artifacts/bijux-canon-reason")
    app = FastAPI(title="bijux-canon-reason", version="1")
    db_path = configure_item_store(artifacts_dir)
    app.state.db_path = db_path

    api_token = os.getenv("RAR_API_TOKEN")
    rate_limit_raw = os.getenv("RAR_API_RATE_LIMIT", "0")
    try:
        rate_limit = int(rate_limit_raw)
    except Exception:  # noqa: BLE001
        rate_limit = 0
    app.state.rate_limit = initialize_rate_limit_state(rate_limit)

    def _guard(request: Request) -> None:
        guard_request(
            request,
            api_token=api_token,
            rate_limit=rate_limit,
            rate_limit_state=app.state.rate_limit,
        )

    @app.middleware("http")
    async def _guard_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        try:
            _guard(request)
            response = await call_next(request)
            return (
                response
                if isinstance(response, Response)
                else JSONResponse(status_code=200, content=str(response))
            )
        except HTTPException as exc:  # pragma: no cover - exercised via tests
            return JSONResponse(
                status_code=exc.status_code, content={"detail": exc.detail}
            )

    @app.exception_handler(RequestValidationError)
    @no_type_check
    async def _validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": "invalid request"})

    @app.get("/health")
    @no_type_check
    def health() -> dict[str, str]:
        return {"status": "ok"}
    register_item_routes(
        app,
        guard_request=_guard,
        enforce_response_size=enforce_response_size,
        max_response_items=MAX_RESPONSE_ITEMS,
        max_offset=MAX_OFFSET,
    )
    register_run_routes(
        app,
        artifacts_dir=artifacts_dir,
        guard_request=_guard,
        max_request_bytes=MAX_REQUEST_BYTES,
    )

    return app


# Default ASGI application for uvicorn entrypoint.
app = create_app()
