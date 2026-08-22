# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi <bijan@bijux.io>
from __future__ import annotations

import json
from pathlib import Path


def _values(value: object) -> list[object]:
    if isinstance(value, dict):
        return [item for child in value.values() for item in _values(child)]
    if isinstance(value, list):
        return [item for child in value for item in _values(child)]
    return [value]


def test_benchmark_baseline_matrix_present() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    baseline_path = repo_root / "benchmarks" / "baselines" / "v0.3.10.json"
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    backends = payload["backends"]
    required = {
        ("sqlite-fts5", "lexical"),
        ("faiss-flat-ip", "exact"),
        ("faiss-hnsw", "ann"),
        ("qdrant", "remote"),
    }
    present = {(entry["backend"], entry["mode"]) for entry in backends}
    missing = required - present
    assert not missing, f"Missing benchmark baselines: {sorted(missing)}"

    values = _values(payload)
    assert None not in values
    assert not any(
        isinstance(value, str) and "todo" in value.lower() for value in values
    )

    statuses = {entry["backend"]: entry["status"] for entry in backends}
    assert statuses == {
        "sqlite-fts5": "measured",
        "faiss-flat-ip": "measured",
        "faiss-hnsw": "measured",
        "qdrant": "experimental_excluded",
    }

    ann = next(entry for entry in backends if entry["backend"] == "faiss-hnsw")
    assert 0.0 <= ann["quality"]["minimum_recall"] <= 1.0
    assert 0.0 <= ann["quality"]["mean_recall"] <= 1.0
    assert ann["quality"]["result_reachability"] == 1.0
    assert payload["restart"]["integrity"] == "verified"
    assert payload["corruption"]["one_byte_hnsw_tamper_refused"] is True
