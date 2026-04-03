# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import json
import os
from pathlib import Path

import schemathesis
from starlette.testclient import TestClient

from bijux_vex.boundaries.api.app import build_app
from bijux_vex.core.identity.ids import fingerprint


def test_api_responses_are_deterministic(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "api.sqlite"
    monkeypatch.setenv("BIJUX_VEX_STATE_PATH", str(db_path))
    app = build_app()
    client = TestClient(app)

    client.post("/create", json={"name": "demo"})
    client.post("/ingest", json={"documents": ["hi"], "vectors": [[0.0, 0.0]]})
    client.post("/artifact", json={"execution_contract": "deterministic"})

    schema = schemathesis.openapi.from_dict(app.openapi())
    operation = schema.find_operation_by_path("post", "/execute")
    assert operation is not None
    case = operation.Case(
        body={
            "vector": [0.0, 0.0],
            "top_k": 1,
            "execution_contract": "deterministic",
            "execution_intent": "exact_validation",
        },
        media_type="application/json",
    )
    payload = case.as_transport_kwargs()
    payload.pop("cookies", None)
    resp1 = client.request(**payload)
    resp2 = client.request(**payload)

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json()
    assert fingerprint(json.dumps(resp1.json(), sort_keys=True)) == fingerprint(
        json.dumps(resp2.json(), sort_keys=True)
    )
