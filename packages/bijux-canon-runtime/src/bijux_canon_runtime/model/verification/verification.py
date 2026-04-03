# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for model/verification/verification.py."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_runtime.model.verification.arbitration_policy import ArbitrationPolicy
from bijux_canon_runtime.model.verification.verification_rule import VerificationRule
from bijux_canon_runtime.spec.ontology import VerificationRandomness
from bijux_canon_runtime.spec.ontology.ids import EvidenceID, RuleID


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
