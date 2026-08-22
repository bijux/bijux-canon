# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Application service for persisted v1 run operations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeAlias, cast

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

JsonDocument: TypeAlias = (
    dict[str, object] | list[object] | str | int | float | bool | None
)


class RunNotFoundError(LookupError):
    """A requested persisted run artifact does not exist."""


class RunResponseTooLargeError(ValueError):
    """A persisted response exceeds the configured transport budget."""


class RunService:
    """Own run creation, persistence inspection, verification, and replay."""

    def __init__(self, *, artifacts_dir: Path, max_request_bytes: int) -> None:
        self._artifacts_dir = artifacts_dir
        self._max_request_bytes = max_request_bytes

    def create_run(
        self, *, spec: ProblemSpec, preset: str, seed: int
    ) -> dict[str, str]:
        """Build and describe a deterministic run."""
        artifacts = RunBuilder().build(
            inputs=RunInputs(spec=spec, preset=preset, seed=seed),
            artifacts_root=self._artifacts_dir,
        )
        fingerprint = artifacts.fingerprint_path.read_text(encoding="utf-8").strip()
        return {
            "run_id": artifacts.run_id,
            "run_dir": str(artifacts.run_dir),
            "trace_id": artifacts.trace.id,
            "fingerprint": fingerprint,
        }

    def get_document(self, *, run_id: str, filename: str) -> JsonDocument:
        """Read and unwrap one canonical run document."""
        path = self._run_dir(run_id) / filename
        if not path.exists():
            raise RunNotFoundError(f"{filename} not found")
        return self._unwrap_canonical_document(read_json_file(path))

    def get_trace(self, *, run_id: str) -> str:
        """Return the persisted trace within the response size budget."""
        path = self._run_dir(run_id) / "trace.jsonl"
        if not path.exists():
            raise RunNotFoundError("trace not found")
        content = path.read_text(encoding="utf-8")
        if len(content.encode("utf-8")) > self._max_request_bytes * 10:
            raise RunResponseTooLargeError("response too large")
        return content

    def verify_run(self, *, run_id: str) -> dict[str, object]:
        """Verify a persisted run and save its report."""
        run_dir = self._run_dir(run_id)
        trace_path = run_dir / "trace.jsonl"
        plan_path = run_dir / "plan.json"
        if not trace_path.exists() or not plan_path.exists():
            raise RunNotFoundError("run artifacts missing")
        trace = read_trace_jsonl(trace_path)
        plan = Plan.model_validate(read_json_file(plan_path))
        report = verify_trace(trace=trace, plan=plan, artifacts_dir=run_dir)
        output_path = run_dir / "verify.verify.json"
        write_json_file(output_path, report.model_dump(mode="json"))
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {"report": payload}

    def replay_run(self, *, run_id: str) -> dict[str, object]:
        """Replay a persisted run and return its comparison."""
        trace_path = self._run_dir(run_id) / "trace.jsonl"
        if not trace_path.exists():
            raise RunNotFoundError("trace not found")
        result, replay_trace_path = replay_from_artifacts(trace_path)
        return {
            "original_trace_fingerprint": result.original_trace_fingerprint,
            "replayed_trace_fingerprint": result.replayed_trace_fingerprint,
            "diff_summary": result.diff_summary,
            "replay_trace_path": str(replay_trace_path),
        }

    def _run_dir(self, run_id: str) -> Path:
        try:
            sanitized_run_id = sanitize_run_id(run_id)
        except ValueError as exc:
            raise RunNotFoundError("run not found") from exc
        return self._artifacts_dir / "runs" / sanitized_run_id

    @staticmethod
    def _unwrap_canonical_document(raw: object) -> JsonDocument:
        if isinstance(raw, dict) and "data" in raw and "canonical_version" in raw:
            return cast(JsonDocument, raw["data"])
        if isinstance(raw, (dict, list, str, int, float, bool)) or raw is None:
            return raw
        return str(raw)


__all__ = [
    "JsonDocument",
    "RunNotFoundError",
    "RunResponseTooLargeError",
    "RunService",
]
