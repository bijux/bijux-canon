# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bijux_rar.httpapi import create_app


@pytest.mark.e2e
@pytest.mark.parametrize(
    "seed,top_k",
    [(0, 1), (1, 1), (2, 2), (3, 2), (4, 3), (5, 3), (6, 4), (7, 4), (8, 5), (9, 5)],
)
def test_api_happy_path_matrix(tmp_path: Path, seed: int, top_k: int) -> None:
    artifacts = tmp_path / "artifacts"
    app = create_app(artifacts_dir=artifacts)
    client = TestClient(app)

    payload = {
        "spec": {
            "description": f"api run seed={seed}",
            "constraints": {"needs_retrieval": True, "top_k": top_k},
            "expected": {},
            "version": 1,
        },
        "preset": "rar",
        "seed": seed,
    }
    r = client.post("/v1/runs", json=payload)
    assert r.status_code == 200, r.text
    out = r.json()
    run_id = out["run_id"]

    r2 = client.get(f"/v1/runs/{run_id}")
    assert r2.status_code == 200
    assert r2.json()["run_id"] == run_id

    r3 = client.get(f"/v1/runs/{run_id}/manifest")
    assert r3.status_code == 200
    manifest = r3.json()
    evidence_keys = [k for k in manifest if k.startswith("evidence/")]
    # Some test corpora have fewer chunks than requested; ensure we wrote evidence and did not exceed top_k.
    assert 1 <= len(evidence_keys) <= top_k

    r4 = client.get(f"/v1/runs/{run_id}/trace")
    assert r4.status_code == 200
    assert "trace_header" in r4.text

    r5 = client.post(f"/v1/runs/{run_id}/verify")
    assert r5.status_code == 200
    assert "checks" in r5.json()

    r6 = client.post(f"/v1/runs/{run_id}/replay")
    assert r6.status_code == 200
    rep = r6.json()
    assert rep["original_trace_fingerprint"] == rep["replayed_trace_fingerprint"]
