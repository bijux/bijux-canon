# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

# SPDX-FileCopyrightText: © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT

from pathlib import Path
import sys

import pytest


@pytest.mark.e2e
def test_cli_verify_span_hash_passes(tmp_path: Path, write_spec, run_cli) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    spec_path = write_spec(
        description="span hash pass",
        constraints={"needs_retrieval": True, "top_k": 1},
    )
    run = run_cli(
        [
            sys.executable,
            "-m",
            "bijux_rar",
            "run",
            "--spec",
            str(spec_path),
            "--seed",
            "0",
            "--preset",
            "rar",
            "--artifacts-dir",
            str(artifacts),
        ],
        check=True,
    )
    run_dir = Path(run.stdout.strip())
    cmd = [
        sys.executable,
        "-m",
        "bijux_rar",
        "verify",
        "--trace",
        str(run_dir / "trace.jsonl"),
        "--plan",
        str(run_dir / "plan.json"),
        "--fail-on-verify",
    ]
    # Should pass without errors.
    run_cli(cmd, check=True)
