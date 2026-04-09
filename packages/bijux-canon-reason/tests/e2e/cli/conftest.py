# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Any

from bijux_canon_reason.core.fingerprints import canonical_dumps
import pytest


@pytest.fixture()
def run_cli() -> Any:
    """Run the CLI against src/ without requiring installation."""

    def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        repo_root = Path(__file__).resolve().parents[3]
        env = dict(os.environ)
        env["PYTHONPATH"] = str(repo_root / "src") + (
            os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else ""
        )
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(  # noqa: S603
            cmd, text=True, capture_output=True, check=check, env=env
        )

    return _run


@pytest.fixture()
def write_spec(tmp_path: Path) -> Any:
    def _write(
        *,
        description: str,
        constraints: dict[str, object],
        expected: dict[str, object] | None = None,
    ) -> Path:
        p = tmp_path / "spec.json"
        obj = {
            "description": description,
            "constraints": constraints,
            "expected": expected or {},
            "version": 1,
        }
        p.write_text(canonical_dumps(obj) + "\n", encoding="utf-8")
        return p

    return _write
