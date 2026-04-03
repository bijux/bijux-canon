# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from pathlib import Path

from fastapi.testclient import TestClient

from bijux_vex.api.v1 import build_app


def test_api_nd_execution_path(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "api.sqlite"
    monkeypatch.setenv("BIJUX_VEX_STATE_PATH", str(db_path))
    monkeypatch.setenv("BIJUX_VEX_BACKEND", "hnsw")
    app = build_app()
    client = TestClient(app)

    assert client.post("/create", json={"name": "demo"}).status_code == 200
    assert (
        client.post("/ingest", json={"documents": ["hi"], "vectors": [[0.0, 1.0]]})
    ).status_code == 200

    resp = client.post("/artifact", json={"execution_contract": "non_deterministic"})
    assert resp.status_code == 200
    artifact_id = resp.json()["artifact_id"]

    payload = {
        "artifact_id": artifact_id,
        "vector": [0.0, 1.0],
        "top_k": 1,
        "execution_contract": "non_deterministic",
        "execution_intent": "exploratory_search",
        "execution_mode": "bounded",
        "execution_budget": {
            "max_latency_ms": 10,
            "max_memory_mb": 10,
            "max_error": 0.2,
        },
        "randomness_profile": {"seed": 7, "sources": ["ann"], "bounded": True},
        "nd_build_on_demand": True,
    }
    exec_resp = client.post("/execute", json=payload)
    assert exec_resp.status_code == 200
    data = exec_resp.json()
    assert data["execution_contract"] == "non_deterministic"
    assert len(data["results"]) == 1
