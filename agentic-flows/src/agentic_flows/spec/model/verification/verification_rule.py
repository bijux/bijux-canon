# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/model/verification/verification_rule.py."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_flows.spec.ontology import VerificationRandomness
from agentic_flows.spec.ontology.ids import RuleID


@dataclass(frozen=True)
class VerificationRule:
    """Verification rule definition; misuse breaks rule evaluation."""

    spec_version: str
    rule_id: RuleID
    description: str
    severity: str
    target: str
    randomness_requirement: VerificationRandomness
    cost: int


__all__ = ["VerificationRule"]
