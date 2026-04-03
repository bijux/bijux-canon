# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from bijux_vex.boundaries.api.app import build_app


def test_v01_api_capabilities_snapshot() -> None:
    app = build_app()
    client = TestClient(app)
    response = client.get("/capabilities")
    assert response.status_code == 200
    payload = response.json()

    snapshot_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "v0_1_api_capabilities.json"
    )
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    for key, value in snapshot.items():
        assert key in payload
        if isinstance(value, list):
            for entry in value:
                if isinstance(entry, dict):
                    assert any(
                        all(item in candidate.items() for item in entry.items())
                        for candidate in payload[key]
                        if isinstance(candidate, dict)
                    )
                else:
                    assert entry in payload[key]
        else:
            assert payload[key] == value
