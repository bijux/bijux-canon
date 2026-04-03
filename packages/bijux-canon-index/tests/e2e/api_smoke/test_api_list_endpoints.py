# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi <bijan@bijux.io>
from __future__ import annotations

from pathlib import Path

from starlette.testclient import TestClient

from bijux_canon_index.api.v1.app import build_app


def test_list_artifacts_and_runs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("BIJUX_CANON_INDEX_STATE_PATH", str(tmp_path / "api.sqlite"))
    monkeypatch.setenv("BIJUX_CANON_INDEX_RUN_DIR", str(tmp_path / "runs"))
    app = build_app()
    client = TestClient(app)

    client.post("/create", json={"name": "demo"})
    client.post("/ingest", json={"documents": ["hi"], "vectors": [[0.0, 0.0]]})
    client.post("/artifact", json={"execution_contract": "deterministic"})
    client.post(
        "/execute",
        json={
            "vector": [0.0, 0.0],
            "top_k": 1,
            "execution_contract": "deterministic",
            "execution_intent": "exact_validation",
            "execution_mode": "strict",
        },
    )

    artifacts = client.get("/artifacts", params={"limit": 10, "offset": 0})
    assert artifacts.status_code == 200
    assert "artifacts" in artifacts.json()

    runs = client.get("/runs", params={"limit": 10, "offset": 0})
    assert runs.status_code == 200
    assert "runs" in runs.json()
