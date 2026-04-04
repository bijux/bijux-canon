# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, no_type_check

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from bijux_canon_reason.application.run_artifacts import RunBuilder, RunInputs
from bijux_canon_reason.core.types import Plan, ProblemSpec
from bijux_canon_reason.interfaces.access_guards import sanitize_run_id
from bijux_canon_reason.interfaces.serialization.json_file import (
    read_json_file,
    write_json_file,
)
from bijux_canon_reason.interfaces.serialization.trace_jsonl import read_trace_jsonl
from bijux_canon_reason.traces.replay import replay_from_artifacts
from bijux_canon_reason.verification.verifier import verify_trace


class RunCreateRequest(BaseModel):
    spec: ProblemSpec
    preset: str = Field(default="default")
    seed: int = Field(default=0, ge=0)


class RunCreateResponse(BaseModel):
    run_id: str
    run_dir: str
    trace_id: str
    fingerprint: str


def register_run_routes(
    app: FastAPI,
    *,
    artifacts_dir: Path,
    guard_request: Any,
    max_request_bytes: int,
) -> None:
    @app.post("/v1/runs", response_model=RunCreateResponse)
    @no_type_check
    def create_run(req: RunCreateRequest, request: Request) -> RunCreateResponse:
        guard_request(request)
        builder = RunBuilder()
        artifacts = builder.build(
            inputs=RunInputs(spec=req.spec, preset=req.preset, seed=req.seed),
            artifacts_root=artifacts_dir,
        )
        fingerprint = artifacts.fingerprint_path.read_text(encoding="utf-8").strip()
        return RunCreateResponse(
            run_id=artifacts.run_id,
            run_dir=str(artifacts.run_dir),
            trace_id=artifacts.trace.id,
            fingerprint=fingerprint,
        )

    @app.get("/v1/runs/{run_id}")
    @no_type_check
    def get_run(run_id: str, request: Request) -> Any:
        guard_request(request)
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
        guard_request(request)
        run_dir = _run_dir(artifacts_dir, run_id)
        path = run_dir / "manifest.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="manifest not found")
        raw = read_json_file(path)
        if isinstance(raw, dict) and "data" in raw and "canonical_version" in raw:
            return raw["data"]
        return raw

    @app.get("/v1/runs/{run_id}/trace", response_class=PlainTextResponse)
    @no_type_check
    def fetch_trace(run_id: str, request: Request) -> str:
        guard_request(request)
        run_dir = _run_dir(artifacts_dir, run_id)
        path = run_dir / "trace.jsonl"
        if not path.exists():
            raise HTTPException(status_code=404, detail="trace not found")
        content = path.read_text(encoding="utf-8")
        if len(content.encode("utf-8")) > max_request_bytes * 10:
            raise HTTPException(status_code=413, detail="response too large")
        return content

    @app.post("/v1/runs/{run_id}/verify")
    @no_type_check
    def verify_run(run_id: str, request: Request) -> Any:
        guard_request(request)
        run_dir = _run_dir(artifacts_dir, run_id)
        trace_path = run_dir / "trace.jsonl"
        plan_path = run_dir / "plan.json"
        if not trace_path.exists() or not plan_path.exists():
            raise HTTPException(status_code=404, detail="run artifacts missing")

        trace = read_trace_jsonl(trace_path)
        plan = Plan.model_validate(read_json_file(plan_path))
        report = verify_trace(trace=trace, plan=plan, artifacts_dir=run_dir)

        output_path = run_dir / "verify.verify.json"
        write_json_file(output_path, report.model_dump(mode="json"))
        return json.loads(output_path.read_text(encoding="utf-8"))

    @app.post("/v1/runs/{run_id}/replay")
    @no_type_check
    def replay_run(run_id: str, request: Request) -> Any:
        guard_request(request)
        run_dir = _run_dir(artifacts_dir, run_id)
        trace_path = run_dir / "trace.jsonl"
        if not trace_path.exists():
            raise HTTPException(status_code=404, detail="trace not found")
        result, replay_trace_path = replay_from_artifacts(trace_path)
        return {
            "original_trace_fingerprint": result.original_trace_fingerprint,
            "replayed_trace_fingerprint": result.replayed_trace_fingerprint,
            "diff_summary": result.diff_summary,
            "replay_trace_path": str(replay_trace_path),
        }


def _run_dir(artifacts_dir: Path, run_id: str) -> Path:
    return artifacts_dir / "runs" / sanitize_run_id(run_id)


__all__ = ["RunCreateRequest", "RunCreateResponse", "register_run_routes"]
