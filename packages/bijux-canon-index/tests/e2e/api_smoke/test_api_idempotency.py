# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi <bijan@bijux.io>
from __future__ import annotations

from pathlib import Path

from starlette.testclient import TestClient

from bijux_canon_index.api.v1.app import build_app


def test_ingest_idempotency_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("BIJUX_CANON_INDEX_STATE_PATH", str(tmp_path / "api.sqlite"))
    app = build_app()
    client = TestClient(app)

    client.post("/create", json={"name": "demo"})
    payload = {"documents": ["hi"], "vectors": [[0.0, 0.0]]}
    resp1 = client.post("/ingest", json=payload, headers={"Idempotency-Key": "abc"})
    resp2 = client.post("/ingest", json=payload, headers={"Idempotency-Key": "abc"})

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json()
