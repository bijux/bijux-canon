# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.contracts.execution_abi import (
    EXECUTION_ABI_VERSION,
    execution_abi_fingerprint,
    execution_abi_payload,
)


EXPECTED_ABI_FINGERPRINT = (
    "02c5e96fdd875cd6732ed26c0c0eb99dd186e70e3c0e6fd1535339bad3d939c6"
)


def test_execution_abi_is_frozen():
    assert EXECUTION_ABI_VERSION == "1.3.21"
    assert execution_abi_fingerprint() == EXPECTED_ABI_FINGERPRINT
    payload = execution_abi_payload()
    assert "execution_request_fields" in payload


def test_execution_abi_payload_is_semantic():
    payload = execution_abi_payload()
    req_fields = tuple(name for name, _, _ in payload["execution_request_fields"])
    artifact_fields = tuple(name for name, _, _ in payload["execution_artifact_fields"])
    result_fields = tuple(name for name, _, _ in payload["execution_result_fields"])
    assert req_fields[:5] == (
        "request_id",
        "text",
        "vector",
        "top_k",
        "execution_contract",
    )
    assert "execution_intent" in req_fields and "execution_mode" in req_fields
    assert artifact_fields[0] == "artifact_id"
    assert "execution_contract" in artifact_fields
    assert "execution_signature" in artifact_fields
    assert "approximation_report" in artifact_fields
    assert "replayable" not in artifact_fields
    assert result_fields[0] == "execution_id"
    assert "status" in result_fields and "failure_reason" in result_fields
