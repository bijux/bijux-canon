# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""FastAPI boundary for bijux-rar (production-hardened).

Endpoints (v1):
  POST /v1/runs           -> create+execute a run (writes artifacts)
  GET  /v1/runs/{run_id}  -> read run_meta.json
  GET  /v1/runs/{run_id}/manifest -> read manifest.json
  GET  /v1/runs/{run_id}/trace    -> stream trace.jsonl
  POST /v1/runs/{run_id}/verify   -> verify trace against plan/evidence
  POST /v1/runs/{run_id}/replay   -> replay using FrozenRuntime

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
import sqlite3
import time
from typing import Any, no_type_check
import uuid

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

from bijux_rar.boundaries.serde.json_file import read_json_file, write_json_file
from bijux_rar.boundaries.serde.trace_jsonl import read_trace_jsonl
from bijux_rar.core.rar_types import Plan, ProblemSpec
from bijux_rar.rar.skeleton.run_builder import RunBuilder, RunInputs
from bijux_rar.rar.traces.replay import replay_from_artifacts
from bijux_rar.rar.verification.verifier import verify_trace
from bijux_rar.security import (
    rate_limit_per_key,
    sanitize_run_id,
)

MAX_REQUEST_BYTES = 8192
MAX_RESPONSE_ITEMS = 100
MAX_OFFSET = 1_000_000
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
DENY_CONTENT_TYPES = {"application/xml", "text/xml"}


class RunCreateRequest(BaseModel):
    spec: ProblemSpec
    preset: str = Field(default="default")
    seed: int = Field(default=0, ge=0)


class RunCreateResponse(BaseModel):
    run_id: str
    run_dir: str
    trace_id: str
    fingerprint: str


class ItemCreate(BaseModel):
    model_config = {"extra": "allow"}
    name: str | None = None
    description: str | None = None


class ItemUpdate(BaseModel):
    model_config = {"extra": "allow"}
    name: str | None = None
    description: str | None = None


def _run_dir(artifacts_dir: Path, run_id: str) -> Path:
    clean = sanitize_run_id(run_id)
    return artifacts_dir / "runs" / clean


def _db_path(artifacts_dir: Path) -> Path:
    return artifacts_dir / "api_storage.db"


def _init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            deleted INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()


def _row_to_item(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
    }


def _validate_item_id(item_id: int) -> None:
    if item_id < 1 or item_id > 1_000_000:
        raise HTTPException(status_code=422, detail="item_id out of range")


def _check_size_limit(request: Request) -> None:
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > MAX_REQUEST_BYTES:
                raise HTTPException(status_code=413, detail="request too large")
        except ValueError:
            pass


def _enforce_response_size(payload: dict[str, object]) -> dict[str, object]:
    # best-effort guard to prevent giant JSON responses
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_RESPONSE_BYTES:
        raise HTTPException(status_code=413, detail="response too large")
    return payload


def create_app(*, artifacts_dir: Path | None = None) -> FastAPI:
    artifacts_dir = artifacts_dir or Path("artifacts")
    app = FastAPI(title="bijux-rar", version="1")
    db_path = _db_path(artifacts_dir)
    _init_db(db_path)
    app.state.db_path = db_path

    api_token = os.getenv("RAR_API_TOKEN")
    rate_limit_raw = os.getenv("RAR_API_RATE_LIMIT", "0")
    try:
        rate_limit = int(rate_limit_raw)
    except Exception:  # noqa: BLE001
        rate_limit = 0
    app.state.rate_limit = {
        "limit": rate_limit,
        "window_start": time.time(),
        "count": 0,
        "buckets": {},
    }

    def _guard(request: Request) -> None:
        _check_size_limit(request)
        supplied = request.headers.get("x-api-token")
        if api_token and supplied != api_token:
            raise HTTPException(status_code=401, detail="unauthorized")
        # Deny disallowed content types early
        if request.headers.get("content-type"):
            ct = request.headers["content-type"].split(";")[0].strip().lower()
            if ct in DENY_CONTENT_TYPES:
                raise HTTPException(status_code=415, detail="unsupported media type")
        if rate_limit > 0:
            bucket = app.state.rate_limit
            try:
                # Per-key limiter; "anon" bucket for unauthenticated traffic
                rate_limit_per_key(bucket, supplied or "anon")
            except PermissionError as exc:
                raise HTTPException(status_code=429, detail=str(exc)) from exc

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

    @app.get("/v1/items")
    @no_type_check
    def list_items(
        request: Request,
        limit: int = Query(default=10, ge=1, le=MAX_RESPONSE_ITEMS),
        offset: int = Query(default=0, ge=0, le=MAX_OFFSET),
    ) -> dict[str, object]:
        _guard(request)
        allowed_keys = {"limit", "offset"}
        extras = [k for k in request.query_params if k not in allowed_keys]
        if extras:
            raise HTTPException(
                status_code=422,
                detail=f"unknown query params: {', '.join(sorted(extras))}",
            )
        conn = sqlite3.connect(app.state.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT id, name, description FROM items
            WHERE deleted = 0
            ORDER BY id ASC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = cur.fetchall()
        total_cur = conn.execute("SELECT COUNT(*) FROM items WHERE deleted = 0")
        total = int(total_cur.fetchone()[0])
        conn.close()
        return _enforce_response_size(
            {"items": [_row_to_item(r) for r in rows], "total": total}
        )

    @app.get("/v1/items/{item_id}")
    @no_type_check
    def get_item(
        request: Request,
        item_id: int = FastPath(ge=1, le=1_000_000),
    ) -> dict[str, object]:
        _guard(request)
        _validate_item_id(item_id)
        conn = sqlite3.connect(app.state.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT id, name, description, deleted FROM items WHERE id = ?", (item_id,)
        )
        row = cur.fetchone()
        if row is None:
            conn.close()
            raise HTTPException(status_code=404, detail="item not found")
        if row["deleted"]:
            conn.close()
            raise HTTPException(status_code=404, detail="item deleted")
        result = _row_to_item(row)
        conn.close()
        return result

    @app.delete("/v1/items/{item_id}", status_code=204)
    @no_type_check
    def delete_item(
        request: Request,
        item_id: int = FastPath(ge=1, le=1_000_000),
    ) -> None:
        _guard(request)
        _validate_item_id(item_id)
        conn = sqlite3.connect(app.state.db_path)
        cur = conn.execute("SELECT deleted FROM items WHERE id = ?", (item_id,))
        row = cur.fetchone()
        if row is None:
            conn.close()
            raise HTTPException(status_code=404, detail="item not found")
        if row[0]:
            conn.close()
            raise HTTPException(status_code=404, detail="item deleted")
        conn.execute("UPDATE items SET deleted = 1 WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
        return None

    @app.post("/v1/items", status_code=201)
    @no_type_check
    def create_item(
        request: Request,
        payload: ItemCreate = Body(default=...),  # noqa: B008
    ) -> dict[str, object]:
        _guard(request)
        raw_name = payload.name or f"item-{uuid.uuid4().hex[:8]}"
        description = payload.description or ""
        conn = sqlite3.connect(app.state.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute(
                "SELECT id, name, description, deleted FROM items WHERE name = ?",
                (raw_name,),
            )
            row = cur.fetchone()
            if row and not row["deleted"]:
                return _row_to_item(row)
            if row and row["deleted"]:
                conn.execute(
                    "UPDATE items SET description = ?, deleted = 0 WHERE id = ?",
                    (description, row["id"]),
                )
                conn.commit()
                cur = conn.execute(
                    "SELECT id, name, description FROM items WHERE id = ?",
                    (row["id"],),
                )
                row = cur.fetchone()
                return _row_to_item(row)
            cur = conn.execute(
                "INSERT INTO items (name, description, deleted) VALUES (?, ?, 0)",
                (raw_name, description),
            )
            item_id = cur.lastrowid
            conn.commit()
            cur = conn.execute(
                "SELECT id, name, description FROM items WHERE id = ?", (item_id,)
            )
            row = cur.fetchone()
            return _row_to_item(row)
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise HTTPException(status_code=409, detail="name already exists") from exc
        except sqlite3.Error as exc:  # pragma: no cover - defensive
            conn.rollback()
            raise HTTPException(status_code=422, detail="invalid request") from exc
        finally:
            conn.close()

    @app.put("/v1/items/{item_id}")
    @no_type_check
    def update_item(  # noqa: B008
        request: Request,
        item_id: int = FastPath(ge=1, le=1_000_000),
        payload: ItemUpdate = Body(default=...),  # noqa: B008
    ) -> dict[str, object]:
        _guard(request)
        _validate_item_id(item_id)
        raw_name = payload.name or f"item-{item_id}"
        description = payload.description
        conn = sqlite3.connect(app.state.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute("SELECT id, deleted FROM items WHERE id = ?", (item_id,))
            row = cur.fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO items (id, name, description, deleted) VALUES (?, ?, ?, 0)",
                    (item_id, raw_name, description or ""),
                )
                conn.commit()
                cur = conn.execute(
                    "SELECT id, name, description FROM items WHERE id = ?", (item_id,)
                )
                new_row = cur.fetchone()
                return _row_to_item(new_row)
            if row["deleted"]:
                raise HTTPException(status_code=404, detail="item deleted")
            conn.execute(
                "UPDATE items SET name = ?, description = ? WHERE id = ?",
                (raw_name, description, item_id),
            )
            conn.commit()
            cur = conn.execute(
                "SELECT id, name, description FROM items WHERE id = ?", (item_id,)
            )
            new_row = cur.fetchone()
            return _row_to_item(new_row)
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise HTTPException(status_code=409, detail="name already exists") from exc
        except sqlite3.Error as exc:  # pragma: no cover - defensive
            conn.rollback()
            raise HTTPException(status_code=422, detail="invalid request") from exc
        finally:
            conn.close()

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
