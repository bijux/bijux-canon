# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""HTTP contract helpers for the runtime API surface."""

from __future__ import annotations

from fastapi import status
from fastapi.responses import JSONResponse

from bijux_canon_runtime.api.v1.schemas import FailureEnvelope

ALLOWED_DETERMINISM_LEVELS = {
    "strict",
    "bounded",
    "probabilistic",
    "unconstrained",
}


def structural_failure_response(
    *,
    status_code: int,
    violated_contract: str,
) -> JSONResponse:
    """Build a structural failure response."""
    return _failure_response(
        status_code=status_code,
        failure_class="structural",
        violated_contract=violated_contract,
    )


def authority_failure_response(
    *,
    status_code: int,
    violated_contract: str,
) -> JSONResponse:
    """Build an authority failure response."""
    return _failure_response(
        status_code=status_code,
        failure_class="authority",
        violated_contract=violated_contract,
    )


def validate_runtime_headers(
    *,
    x_agentic_gate: str | None,
    x_determinism_level: str | None,
    x_policy_fingerprint: str | None,
) -> JSONResponse | None:
    """Validate required runtime headers for mutable API operations."""
    if (
        x_agentic_gate is None
        or x_policy_fingerprint is None
        or x_determinism_level in {None, "", "default"}
    ):
        return authority_failure_response(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            violated_contract="headers_required",
        )
    if x_determinism_level not in ALLOWED_DETERMINISM_LEVELS:
        return authority_failure_response(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            violated_contract="determinism_level_invalid",
        )
    return None


def _failure_response(
    *,
    status_code: int,
    failure_class: str,
    violated_contract: str,
) -> JSONResponse:
    payload = FailureEnvelope(
        failure_class=failure_class,
        reason_code="contradiction_detected",
        violated_contract=violated_contract,
        evidence_ids=[],
        determinism_impact="structural",
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


__all__ = [
    "ALLOWED_DETERMINISM_LEVELS",
    "authority_failure_response",
    "structural_failure_response",
    "validate_runtime_headers",
]
