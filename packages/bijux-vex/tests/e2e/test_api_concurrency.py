# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from bijux_vex.boundaries.api.app import build_app


def test_api_execute_concurrency(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BIJUX_VEX_STATE_PATH", str(tmp_path / "concurrency.sqlite"))
    app = build_app()

    with TestClient(app) as client:
        ingest = client.post(
            "/ingest",
            json={"documents": ["hello"], "vectors": [[0.0, 1.0]]},
        )
        assert ingest.status_code == 200
        artifact = client.post(
            "/artifact",
            json={"execution_contract": "deterministic"},
        )
        assert artifact.status_code == 200
        artifact_id = artifact.json()["artifact_id"]

    payload = {
        "vector": [0.0, 1.0],
        "top_k": 1,
        "artifact_id": artifact_id,
        "execution_contract": "deterministic",
        "execution_intent": "exact_validation",
        "execution_mode": "strict",
    }

    def run_execute() -> dict[str, object]:
        with TestClient(app) as client:
            response = client.post("/execute", json=payload)
            assert response.status_code == 200
            return response.json()

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: run_execute(), range(8)))

    first = results[0]["results"]
    assert all(entry["results"] == first for entry in results)
