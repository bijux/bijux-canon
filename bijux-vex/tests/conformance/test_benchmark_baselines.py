# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import json
import warnings
from pathlib import Path


def test_benchmark_baseline_matrix_present() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    baseline_path = repo_root / "benchmarks" / "baselines" / "v0.2.0.json"
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    runs = payload.get("runs", [])
    required = {
        ("memory", "exact"),
        ("faiss", "exact"),
        ("faiss", "ann"),
        ("qdrant", "exact"),
        ("qdrant", "ann"),
    }
    present = {(r.get("store_backend"), r.get("mode")) for r in runs}
    missing = required - present
    assert not missing, f"Missing benchmark baselines: {sorted(missing)}"

    unavailable = [
        (r.get("store_backend"), r.get("mode"))
        for r in runs
        if r.get("status") == "unavailable"
    ]
    if unavailable:
        warnings.warn(
            f"Benchmarks unavailable for: {sorted(unavailable)}",
            RuntimeWarning,
        )
