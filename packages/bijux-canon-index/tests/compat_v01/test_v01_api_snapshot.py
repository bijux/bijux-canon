# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi <bijan@bijux.io>
from __future__ import annotations

import json
from pathlib import Path

from bijux_canon_index.api.v1.app import build_app
from fastapi.testclient import TestClient


def _assert_expected_subset(actual: object, expected: object) -> None:
    if isinstance(expected, dict):
        assert isinstance(actual, dict)
        for key, value in expected.items():
            assert key in actual
            _assert_expected_subset(actual[key], value)
        return
    if isinstance(expected, list):
        assert isinstance(actual, list)
        for entry in expected:
            assert any(_matches_expected(candidate, entry) for candidate in actual), (
                entry
            )
        return
    assert actual == expected


def _matches_expected(actual: object, expected: object) -> bool:
    try:
        _assert_expected_subset(actual, expected)
    except AssertionError:
        return False
    return True


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
    _assert_expected_subset(payload, snapshot)
