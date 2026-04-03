# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/model/verification/verification_result.py."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_flows.spec.ontology import (
    VerificationPhase,
    VerificationRandomness,
)
from agentic_flows.spec.ontology.ids import ArtifactID, RuleID


@dataclass(frozen=True)
class VerificationResult:
    """Verification result record; misuse breaks verification audit."""

    spec_version: str
    engine_id: str
    status: str
    reason: str
    randomness: VerificationRandomness
    violations: tuple[RuleID, ...]
    checked_artifact_ids: tuple[ArtifactID, ...]
    phase: VerificationPhase
    rules_applied: tuple[RuleID, ...]
    decision: str


__all__ = ["VerificationResult"]
