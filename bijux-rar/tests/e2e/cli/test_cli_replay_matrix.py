# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path
import json
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
def test_cli_replay_fingerprint_matches_original(
    tmp_path: Path, write_spec, run_cli, seed: int, preset: str
) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)

    spec_path = write_spec(
        description=f"replay {preset} {seed}",
        constraints={"needs_retrieval": preset == "rar", "top_k": 2},
    )

    p = run_cli(
        [
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
    )
    run_dir = Path(p.stdout.strip())
    fp = (run_dir / "fingerprint.txt").read_text(encoding="utf-8").strip()

    r = run_cli(
        [
            sys.executable,
            "-m",
            "bijux_rar",
            "replay",
            "--trace",
            str(run_dir / "trace.jsonl"),
        ]
    )
    payload = json.loads(r.stdout)
    assert payload["original_trace_fingerprint"] == fp
    assert (
        payload["original_trace_fingerprint"] == payload["replayed_trace_fingerprint"]
    )
