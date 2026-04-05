# EXPERIMENTAL HTTP API — NOT PRODUCTION READY
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# API stability: v1 frozen; Backward compatibility rules apply.

"""EXPERIMENTAL HTTP API.

NOT GUARANTEED STABLE.
MAY BE REMOVED.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import os
from pathlib import Path
from typing import Annotated

from fastapi import Body, FastAPI, Header, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.routing import Match

from bijux_canon_runtime.api.v1.http_contracts import (
    structural_failure_response,
    validate_runtime_headers,
)
from bijux_canon_runtime.api.v1.schemas import (
    FailureEnvelope,
    FlowRunRequest,
    FlowRunResponse,
    HealthResponse,
    ReadyResponse,
    ReplayRequest,
)
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionStore,
)

app = FastAPI(
    title="bijux-canon-runtime API",
    summary="Contract-enforced execution and replay for the runtime layer.",
    description=(
        "The bijux-canon-runtime HTTP API exposes the v1 execution and replay surface "
        "for flow contracts. It keeps required headers, request envelopes, and replay "
        "acceptability visible at the boundary so failures are reviewable rather than "
        "implicit."
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
            "description": "Operational liveness and readiness signals for the runtime API.",
        },
        {
            "name": "Flows",
            "description": "Flow execution and replay endpoints governed by runtime contracts.",
        },
    ],
)


def _openapi() -> dict[str, object]:
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


FAILURE_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: {
        "description": "Request body could not be parsed.",
        "model": FailureEnvelope,
    },
    status.HTTP_406_NOT_ACCEPTABLE: {
        "description": "Required runtime headers are missing or invalid.",
        "model": FailureEnvelope,
    },
    status.HTTP_422_UNPROCESSABLE_ENTITY: {
        "description": "Request validation failed.",
        "model": FailureEnvelope,
    },
    status.HTTP_501_NOT_IMPLEMENTED: {
        "description": "Flow execution or replay is not implemented yet.",
        "model": FailureEnvelope,
    },
}


@app.middleware("http")
async def method_guard(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Reject disallowed HTTP methods and return a 405 with an Allow header."""
    scope = request.scope
    if scope.get("type") == "http":
        matched = False
        allowed_methods: set[str] = set()
        for route in app.router.routes:
            match, _ = route.matches(scope)
            if match in {Match.FULL, Match.PARTIAL}:
                matched = True
                methods = getattr(route, "methods", None)
                if isinstance(methods, set):
                    allowed_methods.update(methods)
        if matched and request.method not in allowed_methods:
            allow_header = ", ".join(sorted(allowed_methods))
            return JSONResponse(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                content={"detail": "Method Not Allowed"},
                headers={"Allow": allow_header},
            )
    return await call_next(request)


@app.exception_handler(RequestValidationError)
def handle_validation_error(_: Request, __: RequestValidationError) -> JSONResponse:
    """Return a structural failure envelope for request validation errors."""
    return structural_failure_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        violated_contract="request_validation",
    )


@app.exception_handler(StarletteHTTPException)
def handle_starlette_http_exception(
    _: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Return a structural failure envelope for parse errors or pass through non-400s."""
    if exc.status_code == status.HTTP_501_NOT_IMPLEMENTED:
        return structural_failure_response(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            violated_contract="not_implemented",
        )
    if exc.status_code != status.HTTP_400_BAD_REQUEST:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return structural_failure_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        violated_contract="request_parse",
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
def health() -> HealthResponse:
    """Provide a lightweight liveness signal for health checks."""
    # /health = process alive; /ready = storage writable.
    return HealthResponse(status="ok")


@app.get(
    "/ready",
    response_model=ReadyResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Runtime storage is unavailable.",
            "model": ReadyResponse,
        }
    },
    tags=["Health"],
)
@app.get(
    "/api/v1/ready",
    response_model=ReadyResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Runtime storage is unavailable.",
            "model": ReadyResponse,
        }
    },
    tags=["Health"],
)
def ready() -> JSONResponse:
    """Provide a readiness signal without performing deep dependency checks."""
    db_path = os.environ.get("AGENTIC_FLOWS_DB_PATH")
    if not db_path:
        return JSONResponse(status_code=503, content={"ready": False})
    try:
        store = DuckDBExecutionStore(Path(db_path))
        store.close()
    except Exception:
        return JSONResponse(status_code=503, content={"ready": False})
    return JSONResponse(content={"ready": True})


@app.post(
    "/api/v1/flows/run",
    response_model=FlowRunResponse,
    responses=FAILURE_RESPONSES,
    tags=["Flows"],
)
def run_flow(
    _: Annotated[FlowRunRequest, Body(...)],
    x_agentic_gate: str | None = Header(None, alias="X-Agentic-Gate"),
    x_determinism_level: str | None = Header(None, alias="X-Determinism-Level"),
    x_policy_fingerprint: str | None = Header(None, alias="X-Policy-Fingerprint"),
) -> JSONResponse:
    """Deterministic guarantees cover declared contracts and persisted envelopes only; runtime environment, external tools, and policy omissions are explicitly not guaranteed; replay equivalence is expected to fail when headers, policy fingerprints, or dataset identity diverge from the declared contract."""
    failure = validate_runtime_headers(
        x_agentic_gate=x_agentic_gate,
        x_determinism_level=x_determinism_level,
        x_policy_fingerprint=x_policy_fingerprint,
    )
    if failure is not None:
        return failure
    raise StarletteHTTPException(status_code=501, detail="Not implemented")


@app.post(
    "/api/v1/flows/replay",
    response_model=FlowRunResponse,
    responses=FAILURE_RESPONSES,
    tags=["Flows"],
)
def replay_flow(
    _: Annotated[ReplayRequest, Body(...)],
    x_agentic_gate: str | None = Header(None, alias="X-Agentic-Gate"),
    x_determinism_level: str | None = Header(None, alias="X-Determinism-Level"),
    x_policy_fingerprint: str | None = Header(None, alias="X-Policy-Fingerprint"),
) -> JSONResponse:
    """Preconditions: required headers are present, determinism level is valid, and the replay request is well-formed; acceptable replay means differences stay within the declared acceptability threshold; mismatches return FailureEnvelope with failure_class set to authority."""
    failure = validate_runtime_headers(
        x_agentic_gate=x_agentic_gate,
        x_determinism_level=x_determinism_level,
        x_policy_fingerprint=x_policy_fingerprint,
    )
    if failure is not None:
        return failure
    raise StarletteHTTPException(status_code=501, detail="Not implemented")
