# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations
import json
from pathlib import Path

from starlette.testclient import TestClient

from bijux_canon_index.api.v1.app import build_app
from bijux_canon_index.core.identity.ids import fingerprint


def test_api_responses_are_deterministic(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "api.sqlite"
    monkeypatch.setenv("BIJUX_VEX_STATE_PATH", str(db_path))
    app = build_app()
    client = TestClient(app)

    client.post("/create", json={"name": "demo"})
    client.post("/ingest", json={"documents": ["hi"], "vectors": [[0.0, 0.0]]})
    client.post("/artifact", json={"execution_contract": "deterministic"})

    payload = {
        "json": {
            "vector": [0.0, 0.0],
            "top_k": 1,
            "execution_contract": "deterministic",
            "execution_intent": "exact_validation",
        }
    }
    resp1 = client.post("/execute", **payload)
    resp2 = client.post("/execute", **payload)

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json()
    assert fingerprint(json.dumps(resp1.json(), sort_keys=True)) == fingerprint(
        json.dumps(resp2.json(), sort_keys=True)
    )
