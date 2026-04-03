# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bijux_rar.httpapi import create_app


def _app(tmp_path: Path) -> TestClient:
    app = create_app(artifacts_dir=tmp_path)
    return TestClient(app)


def test_api_requires_token_when_configured(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RAR_API_TOKEN", "secret")
    client = _app(tmp_path)
    resp = client.get("/v1/items")
    assert resp.status_code == 401
    assert "unauthorized" in resp.text.lower()


def test_api_rejects_disallowed_content_type(tmp_path: Path) -> None:
    client = _app(tmp_path)
    resp = client.post(
        "/v1/items",
        content=b"<xml/>",
        headers={"content-type": "application/xml", "accept": "application/json"},
    )
    assert resp.status_code == 415


def test_api_offset_guard_blocks_extreme_values(tmp_path: Path) -> None:
    client = _app(tmp_path)
    resp = client.get("/v1/items", params={"offset": str(10**9)})
    assert resp.status_code == 422
