# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/model/verification/verification.py."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_flows.spec.model.verification.arbitration_policy import ArbitrationPolicy
from agentic_flows.spec.model.verification.verification_rule import VerificationRule
from agentic_flows.spec.ontology import VerificationRandomness
from agentic_flows.spec.ontology.ids import EvidenceID, RuleID


@dataclass(frozen=True)
class VerificationPolicy:
    """Verification policy; misuse breaks verification guarantees."""

    spec_version: str
    verification_level: str
    failure_mode: str
    randomness_tolerance: VerificationRandomness
    arbitration_policy: ArbitrationPolicy
    required_evidence: tuple[EvidenceID, ...]
    max_rule_cost: int
    rules: tuple[VerificationRule, ...]
    fail_on: tuple[RuleID, ...]
    escalate_on: tuple[RuleID, ...]


__all__ = ["VerificationPolicy"]
