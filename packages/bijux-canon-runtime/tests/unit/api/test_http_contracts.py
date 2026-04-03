# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from fastapi.testclient import TestClient

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
