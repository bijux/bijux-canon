# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for http_api/v1/schemas.py."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr


class FlowRunRequest(BaseModel):
    """Flow run request; misuse breaks API contract."""

    model_config = ConfigDict(extra="forbid")

    flow_manifest: StrictStr
    inputs_fingerprint: StrictStr
    run_mode: Literal["live", "dry", "observer"]
    dataset_id: StrictStr
    policy_fingerprint: StrictStr


class FlowRunResponse(BaseModel):
    """Flow run response; misuse breaks API contract."""

    model_config = ConfigDict(extra="forbid")

    run_id: StrictStr
    flow_id: StrictStr
    status: Literal["completed", "failed", "cancelled"]
    determinism_class: StrictStr | None = Field(
        default=None,
        description="Determinism class classification when available.",
    )
    environment_fingerprint: StrictStr | None = Field(
        default=None,
        description="Environment fingerprint when available.",
    )
    replay_acceptability: Literal[
        "exact_match",
        "invariant_preserving",
        "statistically_bounded",
    ]
    artifact_count: int


class ReplayRequest(BaseModel):
    """Replay request; misuse breaks API contract."""

    model_config = ConfigDict(extra="forbid")

    run_id: StrictStr
    expected_plan_hash: StrictStr
    acceptability_threshold: Literal[
        "exact_match",
        "invariant_preserving",
        "statistically_bounded",
    ]
    observer_mode: StrictBool


class FailureEnvelope(BaseModel):
    """Failure envelope; misuse breaks error contract."""

    model_config = ConfigDict(extra="forbid")

    failure_class: Literal["structural", "semantic", "environmental", "authority"]
    reason_code: Literal["contradiction_detected"]
    violated_contract: StrictStr
    evidence_ids: list[StrictStr]
    determinism_impact: Literal[
        "structural",
        "environmental",
        "stochastic",
        "human",
        "external",
    ]
