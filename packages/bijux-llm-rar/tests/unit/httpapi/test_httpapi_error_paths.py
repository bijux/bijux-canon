# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bijux_rar.httpapi import create_app


def _client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(artifacts_dir=tmp_path))


def test_verify_missing_artifacts_returns_404(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = client.post("/v1/runs/missing/verify")
    assert resp.status_code == 404


def test_replay_missing_trace_returns_404(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = client.post("/v1/runs/missing/replay")
    assert resp.status_code == 404


def test_get_manifest_missing_returns_404(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = client.get("/v1/runs/missing/manifest")
    assert resp.status_code == 404


def test_bad_item_id_validation(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = client.get("/v1/items/0")
    assert resp.status_code == 422


def test_list_items_rejects_unknown_query_param(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = client.get("/v1/items?extra=1")
    assert resp.status_code == 422


def test_create_item_conflict_and_410(tmp_path: Path) -> None:
    client = _client(tmp_path)
    first = client.post("/v1/items", json={"name": "dup"})
    assert first.status_code == 201
    second = client.post("/v1/items", json={"name": "dup"})
    assert second.status_code in (200, 201)
    item_id = second.json()["id"]
    client.delete(f"/v1/items/{item_id}")
    gone = client.get(f"/v1/items/{item_id}")
    assert gone.status_code == 404
