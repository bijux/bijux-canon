# EXPERIMENTAL HTTP API — NOT PRODUCTION READY
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi
# API stability: v1 frozen; Backward compatibility rules apply.

"""EXPERIMENTAL HTTP API.

NOT GUARANTEED STABLE.
MAY BE REMOVED.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from fastapi import Body, FastAPI, Header, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Match

from agentic_flows.http_api.v1.schemas import (
    FailureEnvelope,
    FlowRunRequest,
    ReplayRequest,
)
from agentic_flows.runtime.observability.storage.execution_store import (
    DuckDBExecutionWriteStore,
)

app = FastAPI(
    title="agentic-flows",
    description="HTTP API exposing the same contracts as the CLI.",
    version="0.1",
)


@app.middleware("http")
async def method_guard(request: Request, call_next) -> JSONResponse:
    """Reject disallowed HTTP methods and return a 405 with an Allow header."""
    scope = request.scope
    if scope.get("type") == "http":
        matched = False
        allowed_methods: set[str] = set()
        for route in app.router.routes:
            match, _ = route.matches(scope)
            if match in {Match.FULL, Match.PARTIAL}:
                matched = True
                if route.methods:
                    allowed_methods.update(route.methods)
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
    payload = FailureEnvelope(
        failure_class="structural",
        reason_code="contradiction_detected",
        violated_contract="request_validation",
        evidence_ids=[],
        determinism_impact="structural",
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=payload.model_dump(),
    )


@app.exception_handler(StarletteHTTPException)
def handle_starlette_http_exception(
    _: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Return a structural failure envelope for parse errors or pass through non-400s."""
    if exc.status_code == status.HTTP_501_NOT_IMPLEMENTED:
        payload = FailureEnvelope(
            failure_class="structural",
            reason_code="contradiction_detected",
            violated_contract="not_implemented",
            evidence_ids=[],
            determinism_impact="structural",
        )
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content=payload.model_dump(),
        )
    if exc.status_code != status.HTTP_400_BAD_REQUEST:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    payload = FailureEnvelope(
        failure_class="structural",
        reason_code="contradiction_detected",
        violated_contract="request_parse",
        evidence_ids=[],
        determinism_impact="structural",
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=payload.model_dump(),
    )


@app.get("/health")
@app.get("/api/v1/health")
def health() -> dict[str, str]:
    """Provide a lightweight liveness signal for health checks."""
    # /health = process alive; /ready = storage writable.
    return {"status": "ok"}


@app.get("/ready")
@app.get("/api/v1/ready")
def ready() -> dict[str, str]:
    """Provide a readiness signal without performing deep dependency checks."""
    db_path = os.environ.get("AGENTIC_FLOWS_DB_PATH")
    if not db_path:
        return JSONResponse(status_code=503, content={"ready": False})
    try:
        DuckDBExecutionWriteStore(Path(db_path))
    except Exception:
        return JSONResponse(status_code=503, content={"ready": False})
    return {"ready": True}


@app.post("/api/v1/flows/run")
def run_flow(
    _: Annotated[FlowRunRequest, Body(...)],
    x_agentic_gate: str | None = Header(None, alias="X-Agentic-Gate"),
    x_determinism_level: str | None = Header(None, alias="X-Determinism-Level"),
    x_policy_fingerprint: str | None = Header(None, alias="X-Policy-Fingerprint"),
) -> JSONResponse:
    """Deterministic guarantees cover declared contracts and persisted envelopes only; runtime environment, external tools, and policy omissions are explicitly not guaranteed; replay equivalence is expected to fail when headers, policy fingerprints, or dataset identity diverge from the declared contract."""
    if (
        x_agentic_gate is None
        or x_policy_fingerprint is None
        or x_determinism_level in {None, "", "default"}
    ):
        payload = FailureEnvelope(
            failure_class="authority",
            reason_code="contradiction_detected",
            violated_contract="headers_required",
            evidence_ids=[],
            determinism_impact="structural",
        )
        return JSONResponse(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            content=payload.model_dump(),
        )
    allowed_levels = {"strict", "bounded", "probabilistic", "unconstrained"}
    if x_determinism_level not in allowed_levels:
        payload = FailureEnvelope(
            failure_class="authority",
            reason_code="contradiction_detected",
            violated_contract="determinism_level_invalid",
            evidence_ids=[],
            determinism_impact="structural",
        )
        return JSONResponse(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            content=payload.model_dump(),
        )
    raise StarletteHTTPException(status_code=501, detail="Not implemented")


@app.post("/api/v1/flows/replay")
def replay_flow(
    _: Annotated[ReplayRequest, Body(...)],
    x_agentic_gate: str | None = Header(None, alias="X-Agentic-Gate"),
    x_determinism_level: str | None = Header(None, alias="X-Determinism-Level"),
    x_policy_fingerprint: str | None = Header(None, alias="X-Policy-Fingerprint"),
) -> JSONResponse:
    """Preconditions: required headers are present, determinism level is valid, and the replay request is well-formed; acceptable replay means differences stay within the declared acceptability threshold; mismatches return FailureEnvelope with failure_class set to authority."""
    if (
        x_agentic_gate is None
        or x_policy_fingerprint is None
        or x_determinism_level in {None, "", "default"}
    ):
        payload = FailureEnvelope(
            failure_class="authority",
            reason_code="contradiction_detected",
            violated_contract="headers_required",
            evidence_ids=[],
            determinism_impact="structural",
        )
        return JSONResponse(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            content=payload.model_dump(),
        )
    allowed_levels = {"strict", "bounded", "probabilistic", "unconstrained"}
    if x_determinism_level not in allowed_levels:
        payload = FailureEnvelope(
            failure_class="authority",
            reason_code="contradiction_detected",
            violated_contract="determinism_level_invalid",
            evidence_ids=[],
            determinism_impact="structural",
        )
        return JSONResponse(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            content=payload.model_dump(),
        )
    raise StarletteHTTPException(status_code=501, detail="Not implemented")
