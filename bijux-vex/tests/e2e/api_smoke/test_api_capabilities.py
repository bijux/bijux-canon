# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from fastapi.testclient import TestClient

from bijux_vex.boundaries.api.app import build_app


def test_api_capabilities_reports_backend():
    app = build_app()
    client = TestClient(app)
    resp = client.get("/capabilities")
    assert resp.status_code == 200
    data = resp.json()
    assert "backend" in data and "supports_ann" in data
    assert isinstance(data["contracts"], list)
    assert "execution_modes" in data and isinstance(data["execution_modes"], list)
    assert data["ann_status"] in {"experimental", "unavailable", "stable"}
    assert isinstance(data["storage_backends"], list)
    assert isinstance(data["vector_stores"], list)
