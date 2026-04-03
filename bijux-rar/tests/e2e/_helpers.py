# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""
Shared E2E helpers.

SPDX-FileCopyrightText: © 2025 Bijan Mousavi
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from bijux_rar.core.fingerprints import canonical_dumps


def run_cli(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run CLI with repo-local PYTHONPATH so editable install is not required."""
    repo_root = Path(__file__).resolve().parents[2]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root / "src") + (
        os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else ""
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    full_cmd = cmd
    if not cmd or cmd[0] != sys.executable:
        full_cmd = [sys.executable, "-m", "bijux_rar", *cmd]
    return subprocess.run(  # noqa: S603
        full_cmd,
        text=True,
        capture_output=True,
        check=check,
        env=env,
    )


def write_spec(path: Path, *, description: str, constraints: dict[str, Any]) -> None:
    obj = {
        "description": description,
        "constraints": constraints,
        "version": 1,
    }
    path.write_text(canonical_dumps(obj) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
