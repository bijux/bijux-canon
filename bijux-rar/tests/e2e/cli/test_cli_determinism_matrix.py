# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path
import sys

import pytest


@pytest.mark.e2e
@pytest.mark.parametrize(
    "seed,preset",
    [
        (0, "default"),
        (1, "default"),
        (2, "default"),
        (3, "default"),
        (4, "default"),
        (0, "rar"),
        (1, "rar"),
        (2, "rar"),
        (3, "rar"),
        (4, "rar"),
    ],
)
def test_cli_run_is_deterministic_across_invocations(
    tmp_path: Path, write_spec, run_cli, seed: int, preset: str
) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)

    spec_path = write_spec(
        description=f"determinism {preset} {seed}",
        constraints={"needs_retrieval": preset == "rar", "top_k": 2},
    )

    cmd = [
        sys.executable,
        "-m",
        "bijux_rar",
        "run",
        "--spec",
        str(spec_path),
        "--seed",
        str(seed),
        "--preset",
        preset,
        "--artifacts-dir",
        str(artifacts),
    ]

    p1 = run_cli(cmd)
    run_dir = Path(p1.stdout.strip())
    fp1 = (run_dir / "fingerprint.txt").read_text(encoding="utf-8").strip()

    p2 = run_cli(cmd)
    run_dir2 = Path(p2.stdout.strip())
    fp2 = (run_dir2 / "fingerprint.txt").read_text(encoding="utf-8").strip()

    assert run_dir == run_dir2
    assert fp1 == fp2
