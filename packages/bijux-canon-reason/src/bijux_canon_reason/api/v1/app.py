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
import json
import os
from pathlib import Path
from typing import Any, no_type_check

from fastapi import (
    Body,
    FastAPI,
    HTTPException,
    Query,
    Request,
)
from fastapi import (
    Path as FastPath,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field

from bijux_canon_reason.api.v1.http_guards import (
    MAX_OFFSET,
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_ITEMS,
    enforce_response_size,
    guard_request,
    initialize_rate_limit_state,
)
from bijux_canon_reason.api.v1.item_routes import configure_item_store, register_item_routes
from bijux_canon_reason.application.run_artifacts import RunBuilder, RunInputs
from bijux_canon_reason.core.types import Plan, ProblemSpec
from bijux_canon_reason.interfaces.serialization.json_file import read_json_file, write_json_file
from bijux_canon_reason.interfaces.serialization.trace_jsonl import read_trace_jsonl
from bijux_canon_reason.traces.replay import replay_from_artifacts
from bijux_canon_reason.verification.verifier import verify_trace
from bijux_canon_reason.interfaces.access_guards import sanitize_run_id


class RunCreateRequest(BaseModel):
    spec: ProblemSpec
    preset: str = Field(default="default")
    seed: int = Field(default=0, ge=0)


class RunCreateResponse(BaseModel):
    run_id: str
    run_dir: str
    trace_id: str
    fingerprint: str


def _run_dir(artifacts_dir: Path, run_id: str) -> Path:
    clean = sanitize_run_id(run_id)
    return artifacts_dir / "runs" / clean


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

    @app.post("/v1/runs", response_model=RunCreateResponse)
    @no_type_check
    def create_run(req: RunCreateRequest, request: Request) -> RunCreateResponse:
        _guard(request)
        builder = RunBuilder()
        arts = builder.build(
            inputs=RunInputs(spec=req.spec, preset=req.preset, seed=req.seed),
            artifacts_root=artifacts_dir,
        )
        fp = arts.fingerprint_path.read_text(encoding="utf-8").strip()
        return RunCreateResponse(
            run_id=arts.run_id,
            run_dir=str(arts.run_dir),
            trace_id=arts.trace.id,
            fingerprint=fp,
        )

    @app.get("/v1/runs/{run_id}")
    @no_type_check
    def get_run(run_id: str, request: Request) -> Any:
        _guard(request)
        run_dir = _run_dir(artifacts_dir, run_id)
        meta = run_dir / "run_meta.json"
        if not meta.exists():
            raise HTTPException(status_code=404, detail="run not found")
        raw = read_json_file(meta)
        if isinstance(raw, dict) and "data" in raw and "canonical_version" in raw:
            return raw["data"]
        return raw

    @app.get("/v1/runs/{run_id}/manifest")
    @no_type_check
    def get_manifest(run_id: str, request: Request) -> Any:
        _guard(request)
        run_dir = _run_dir(artifacts_dir, run_id)
        p = run_dir / "manifest.json"
        if not p.exists():
            raise HTTPException(status_code=404, detail="manifest not found")
        raw = read_json_file(p)
        if isinstance(raw, dict) and "data" in raw and "canonical_version" in raw:
            return raw["data"]
        return raw

    @app.get("/v1/runs/{run_id}/trace", response_class=PlainTextResponse)
    @no_type_check
    def fetch_trace(run_id: str, request: Request) -> str:
        _guard(request)
        run_dir = _run_dir(artifacts_dir, run_id)
        p = run_dir / "trace.jsonl"
        if not p.exists():
            raise HTTPException(status_code=404, detail="trace not found")
        content = p.read_text(encoding="utf-8")
        if len(content.encode("utf-8")) > MAX_REQUEST_BYTES * 10:
            raise HTTPException(status_code=413, detail="response too large")
        return content

    @app.post("/v1/runs/{run_id}/verify")
    @no_type_check
    def verify_run(run_id: str, request: Request) -> Any:
        _guard(request)
        run_dir = _run_dir(artifacts_dir, run_id)
        trace_path = run_dir / "trace.jsonl"
        plan_path = run_dir / "plan.json"
        if not trace_path.exists() or not plan_path.exists():
            raise HTTPException(status_code=404, detail="run artifacts missing")

        tr = read_trace_jsonl(trace_path)
        pl = Plan.model_validate(read_json_file(plan_path))
        report = verify_trace(trace=tr, plan=pl, artifacts_dir=run_dir)

        out = run_dir / "verify.verify.json"
        write_json_file(out, report.model_dump(mode="json"))
        return json.loads(out.read_text(encoding="utf-8"))

    @app.post("/v1/runs/{run_id}/replay")
    @no_type_check
    def replay_run(run_id: str, request: Request) -> Any:
        _guard(request)
        run_dir = _run_dir(artifacts_dir, run_id)
        trace_path = run_dir / "trace.jsonl"
        if not trace_path.exists():
            raise HTTPException(status_code=404, detail="trace not found")
        res, replay_trace_path = replay_from_artifacts(trace_path)
        return {
            "original_trace_fingerprint": res.original_trace_fingerprint,
            "replayed_trace_fingerprint": res.replayed_trace_fingerprint,
            "diff_summary": res.diff_summary,
            "replay_trace_path": str(replay_trace_path),
        }

    return app


# Default ASGI application for uvicorn entrypoint.
app = create_app()
