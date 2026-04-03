# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from starlette.testclient import TestClient

from bijux_vex.boundaries.api.app import build_app


def test_ingest_idempotency_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("BIJUX_VEX_STATE_PATH", str(tmp_path / "api.sqlite"))
    app = build_app()
    client = TestClient(app)

    client.post("/create", json={"name": "demo"})
    payload = {"documents": ["hi"], "vectors": [[0.0, 0.0]]}
    resp1 = client.post("/ingest", json=payload, headers={"Idempotency-Key": "abc"})
    resp2 = client.post("/ingest", json=payload, headers={"Idempotency-Key": "abc"})

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json()
