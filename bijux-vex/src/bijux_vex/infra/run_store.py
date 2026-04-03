# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any

from bijux_vex.core.errors import ValidationError


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    tmp.replace(path)


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    status: str
    metadata: dict[str, Any]
    result: dict[str, Any] | None = None


class RunStore:
    def __init__(self, base_dir: str | Path | None = None) -> None:
        base = base_dir or os.getenv("BIJUX_VEX_RUN_DIR") or "runs"
        self._base = Path(base)

    def start(self, run_id: str, metadata: dict[str, Any]) -> None:
        run_dir = self._base / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write(run_dir / "status.json", {"status": "incomplete"})
        _atomic_write(run_dir / "metadata.json", metadata)

    def finalize(self, run_id: str, result: dict[str, Any]) -> None:
        run_dir = self._base / run_id
        if not run_dir.exists():
            raise ValidationError(message="Run directory missing")
        _atomic_write(run_dir / "result.json", result)
        _atomic_write(run_dir / "status.json", {"status": "complete"})

    def mark_failed(
        self, run_id: str, reason: str, details: dict[str, Any] | None = None
    ) -> None:
        run_dir = self._base / run_id
        if not run_dir.exists():
            return
        payload: dict[str, Any] = {"status": "failed", "reason": reason}
        if details:
            payload["details"] = details
        _atomic_write(run_dir / "status.json", payload)

    def load(self, run_id: str) -> RunRecord:
        run_dir = self._base / run_id
        if not run_dir.exists():
            raise ValidationError(message="Run not found")
        status_payload = json.loads(
            (run_dir / "status.json").read_text(encoding="utf-8")
        )
        status = status_payload.get("status", "unknown")
        metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
        result_path = run_dir / "result.json"
        result = (
            json.loads(result_path.read_text(encoding="utf-8"))
            if result_path.exists()
            else None
        )
        if status != "complete":
            raise ValidationError(
                message=f"Run status is {status}; run is not complete"
            )
        return RunRecord(run_id=run_id, status=status, metadata=metadata, result=result)

    def list_runs(self, *, limit: int | None = None, offset: int = 0) -> list[str]:
        if not self._base.exists():
            return []
        entries = sorted(p.name for p in self._base.iterdir() if p.is_dir())
        if offset:
            entries = entries[offset:]
        if limit is not None:
            entries = entries[:limit]
        return entries


__all__ = ["RunStore", "RunRecord"]
