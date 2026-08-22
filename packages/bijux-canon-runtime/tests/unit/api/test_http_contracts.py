# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from bijux_canon_runtime.api.v1.app import app

client = TestClient(app)


def _run_payload() -> dict[str, object]:
    return {
        "flow_manifest": "manifest",
        "inputs_fingerprint": "inputs",
        "run_mode": "live",
        "dataset_id": "dataset",
        "policy_fingerprint": "policy",
    }


def _replay_payload() -> dict[str, object]:
    return {
        "run_id": "run-1",
        "expected_plan_hash": "plan-hash",
        "acceptability_threshold": "exact_match",
        "observer_mode": False,
    }


def test_run_flow_requires_runtime_headers() -> None:
    response = client.post("/api/v1/flows/run", json=_run_payload())

    assert response.status_code == 406
    assert response.json()["violated_contract"] == "headers_required"


def test_replay_flow_rejects_invalid_determinism_header() -> None:
    response = client.post(
        "/api/v1/flows/replay",
        headers={
            "X-Agentic-Gate": "allowed",
            "X-Determinism-Level": "default",
            "X-Policy-Fingerprint": "policy",
        },
        json=_replay_payload(),
    )

    assert response.status_code == 406
    assert response.json()["violated_contract"] == "headers_required"


def test_run_flow_rejects_unknown_determinism_header() -> None:
    response = client.post(
        "/api/v1/flows/run",
        headers={
            "X-Agentic-Gate": "allowed",
            "X-Determinism-Level": "chaotic",
            "X-Policy-Fingerprint": "policy",
        },
        json=_run_payload(),
    )

    assert response.status_code == 406
    assert response.json()["violated_contract"] == "determinism_level_invalid"


def test_readiness_uses_canonical_configuration_precedence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checked: list[Path] = []
    monkeypatch.setenv("AGENTIC_FLOWS_DB_PATH", "legacy.duckdb")
    monkeypatch.setenv("BIJUX_CANON_RUNTIME_DB_PATH", "canonical.duckdb")
    app_module = importlib.import_module("bijux_canon_runtime.api.v1.app")

    class Readiness:
        def __init__(self, configuration, *, environment):
            del environment
            checked.append(configuration.database_path)

        def evaluate(self):
            return SimpleNamespace(ready=True)

    monkeypatch.setattr(app_module, "RuntimeReadinessService", Readiness)

    response = client.get("/ready")

    assert response.status_code == 200
    assert checked == [Path("canonical.duckdb")]
