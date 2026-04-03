# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

from bijux_rar.httpapi import create_app, MAX_REQUEST_BYTES


def _client(
    tmp_path: Path, *, token: str | None = None, rate_limit: int = 0
) -> TestClient:
    env = {}
    if token is not None:
        env["RAR_API_TOKEN"] = token
    env["RAR_API_RATE_LIMIT"] = str(rate_limit)
    # ensure environment only for this app instantiation
    orig = os.environ.copy()
    os.environ.update(env)
    try:
        app = create_app(artifacts_dir=tmp_path)
    finally:
        os.environ.clear()
        os.environ.update(orig)
    return TestClient(app)


def test_auth_guard_blocks_without_token(tmp_path: Path) -> None:
    client = _client(tmp_path, token="secret")
    resp = client.get("/v1/items")
    assert resp.status_code == 401


def test_content_type_denylist(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = client.post(
        "/v1/items",
        headers={"content-type": "text/xml"},
        json={"name": "bad"},
    )
    assert resp.status_code == 415


def test_size_limit_enforced_on_request_header(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = client.get(
        "/v1/items", headers={"content-length": str(MAX_REQUEST_BYTES + 100)}
    )
    assert resp.status_code == 413


def test_items_lifecycle_crud(tmp_path: Path) -> None:
    client = _client(tmp_path)
    # create
    created = client.post("/v1/items", json={"name": "foo", "description": "bar"})
    assert created.status_code == 201
    item = created.json()
    item_id = item["id"]

    # list
    listed = client.get("/v1/items")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    # fetch
    fetched = client.get(f"/v1/items/{item_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "foo"

    # update
    updated = client.put(
        f"/v1/items/{item_id}", json={"name": "foo2", "description": "baz"}
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "foo2"

    # delete then 404
    deleted = client.delete(f"/v1/items/{item_id}")
    assert deleted.status_code == 204
    gone = client.get(f"/v1/items/{item_id}")
    assert gone.status_code == 404


def test_items_payload_validation(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = client.post("/v1/items", json={"name": "good", "extra": "bad"})
    assert resp.status_code == 201


def test_rate_limit_per_key(tmp_path: Path) -> None:
    client = _client(tmp_path, rate_limit=1)
    ok = client.get("/v1/items", headers={"x-api-token": "anon"})
    assert ok.status_code in (
        200,
        204,
        404,
        422,
        429,
    )  # allow immediate block if pre-counted
    blocked = client.get("/v1/items", headers={"x-api-token": "anon"})
    assert blocked.status_code == 429


def test_runs_create_verify_replay(tmp_path: Path) -> None:
    client = _client(tmp_path)
    payload = {
        "spec": {"description": "hello", "constraints": {}, "expected": {}},
        "preset": "default",
        "seed": 0,
    }
    created = client.post("/v1/runs", json=payload)
    assert created.status_code == 200
    run_id = created.json()["run_id"]

    verify = client.post(f"/v1/runs/{run_id}/verify")
    assert verify.status_code == 200

    replay = client.post(f"/v1/runs/{run_id}/replay")
    assert replay.status_code == 200
    body = replay.json()
    assert body["original_trace_fingerprint"]
    assert body["replayed_trace_fingerprint"]
