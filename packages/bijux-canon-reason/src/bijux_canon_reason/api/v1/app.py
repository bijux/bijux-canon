# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""FastAPI application for bijux-canon-reason."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, Response

from bijux_canon_reason.api.v1.http_guards import (
    MAX_OFFSET,
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_ITEMS,
    enforce_response_size,
    guard_request,
    initialize_rate_limit_state,
)
from bijux_canon_reason.api.v1.item_routes import (
    configure_item_store,
    register_item_routes,
)
from bijux_canon_reason.api.v1.openapi_models import ErrorDetail, HealthResponse
from bijux_canon_reason.api.v1.run_routes import register_run_routes

RequestGuard = Callable[[Request], None]
NextHandler = Callable[[Request], Awaitable[Response]]


def create_app(*, artifacts_dir: Path | None = None) -> FastAPI:
    """Create app."""
    artifacts_root = artifacts_dir or Path("artifacts/bijux-canon-reason")
    app = FastAPI(
        title="bijux-canon-reason API",
        summary="Deterministic item and run management for the reasoning runtime.",
        description=(
            "The bijux-canon-reason HTTP API exposes the v1 operational surface for "
            "managing lightweight item state and creating auditable run artifacts. "
            "It is intentionally split between simple CRUD and run lifecycle endpoints "
            "so operators can review stored state and generated reasoning evidence with "
            "the same contract boundary."
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
                "name": "Health",
                "description": "Operational health signals for the reasoning API.",
            },
            {
                "name": "Items",
                "description": "Lightweight persisted items owned by the runtime.",
            },
            {
                "name": "Runs",
                "description": "Run creation, inspection, verification, and replay endpoints.",
            },
        ],
    )
    app.state.db_path = configure_item_store(artifacts_root)

    rate_limit = _read_rate_limit()
    app.state.rate_limit = initialize_rate_limit_state(rate_limit)
    request_guard = _build_request_guard(
        api_token=os.getenv("RAR_API_TOKEN"),
        rate_limit=rate_limit,
        rate_limit_state=app.state.rate_limit,
    )

    _install_guard_middleware(app, request_guard)
    _install_validation_handler(app)

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["Health"],
        summary="Report API health",
        description="Return a lightweight liveness signal for the reasoning API.",
        operation_id="getReasonHealth",
        responses={
            400: {
                "description": "The health request could not be interpreted.",
                "model": ErrorDetail,
            },
        },
    )
    def health() -> dict[str, str]:
        """Handle health."""
        return {"status": "ok"}

    register_item_routes(
        app,
        guard_request=request_guard,
        enforce_response_size=enforce_response_size,
        max_response_items=MAX_RESPONSE_ITEMS,
        max_offset=MAX_OFFSET,
    )
    register_run_routes(
        app,
        artifacts_dir=artifacts_root,
        guard_request=request_guard,
        max_request_bytes=MAX_REQUEST_BYTES,
    )
    _install_openapi_schema(app)
    return app


def _read_rate_limit() -> int:
    """Read rate limit."""
    rate_limit_raw = os.getenv("RAR_API_RATE_LIMIT", "0")
    try:
        return int(rate_limit_raw)
    except ValueError:
        return 0


def _build_request_guard(
    *,
    api_token: str | None,
    rate_limit: int,
    rate_limit_state: dict[str, object],
) -> RequestGuard:
    """Build request guard."""
    def _guard(request: Request) -> None:
        """Handle guard."""
        guard_request(
            request,
            api_token=api_token,
            rate_limit=rate_limit,
            rate_limit_state=rate_limit_state,
        )

    return _guard


def _install_guard_middleware(app: FastAPI, request_guard: RequestGuard) -> None:
    """Install guard middleware."""

    @app.middleware("http")
    async def _guard_middleware(request: Request, call_next: NextHandler) -> Response:
        """Handle guard middleware."""
        try:
            request_guard(request)
            response = await call_next(request)
            if isinstance(response, Response):
                return response
            return JSONResponse(status_code=200, content=str(response))
        except HTTPException as exc:  # pragma: no cover - exercised via tests
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
            )


def _install_validation_handler(app: FastAPI) -> None:
    """Install validation handler."""

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle validation handler."""
        del request, exc
        return JSONResponse(status_code=422, content={"detail": "invalid request"})


def _install_openapi_schema(app: FastAPI) -> None:
    """Install OpenAPI schema."""
    def _openapi() -> dict[str, object]:
        """Handle OpenAPI."""
        if app.openapi_schema is not None:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            summary=app.summary,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
            servers=app.servers,
            contact=app.contact,
            license_info=app.license_info,
        )
        schema["security"] = []
        app.openapi_schema = schema
        return schema

    app.openapi = _openapi


app = create_app()
