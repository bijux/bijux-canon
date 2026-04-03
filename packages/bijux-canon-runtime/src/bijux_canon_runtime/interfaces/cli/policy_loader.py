# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Verification policy loading helpers for the runtime CLI."""

from __future__ import annotations

import json
from pathlib import Path

from bijux_canon_runtime.model.verification.arbitration_policy import ArbitrationPolicy
from bijux_canon_runtime.model.verification.verification import VerificationPolicy
from bijux_canon_runtime.model.verification.verification_rule import VerificationRule
from bijux_canon_runtime.ontology import ArbitrationRule, VerificationRandomness
from bijux_canon_runtime.ontology.ids import EvidenceID, RuleID


def load_policy(path: Path) -> VerificationPolicy:
    """Load a runtime verification policy from a JSON file."""
    raw_contents = path.read_text(encoding="utf-8")
    payload = json.loads(raw_contents)
    arbitration = payload["arbitration_policy"]
    rules = tuple(
        VerificationRule(
            spec_version=rule["spec_version"],
            rule_id=RuleID(rule["rule_id"]),
            description=rule["description"],
            severity=rule["severity"],
            target=rule["target"],
            randomness_requirement=VerificationRandomness(
                rule["randomness_requirement"]
            ),
            cost=int(rule["cost"]),
        )
        for rule in payload["rules"]
    )
    return VerificationPolicy(
        spec_version=payload["spec_version"],
        verification_level=payload["verification_level"],
        failure_mode=payload["failure_mode"],
        randomness_tolerance=VerificationRandomness(payload["randomness_tolerance"]),
        arbitration_policy=ArbitrationPolicy(
            spec_version=arbitration["spec_version"],
            rule=ArbitrationRule(arbitration["rule"]),
            quorum_threshold=arbitration["quorum_threshold"],
        ),
        required_evidence=tuple(
            EvidenceID(value) for value in payload["required_evidence"]
        ),
        max_rule_cost=int(payload["max_rule_cost"]),
        rules=rules,
        fail_on=tuple(RuleID(value) for value in payload["fail_on"]),
        escalate_on=tuple(RuleID(value) for value in payload["escalate_on"]),
    )


__all__ = ["load_policy"]
