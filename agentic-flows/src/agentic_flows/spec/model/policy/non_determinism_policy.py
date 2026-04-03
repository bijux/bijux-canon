# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/model/policy/non_determinism_policy.py."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_flows.core.errors import NonDeterminismViolationError
from agentic_flows.spec.model.execution.non_deterministic_intent import (
    NonDeterministicIntent,
)
from agentic_flows.spec.ontology import EntropyMagnitude
from agentic_flows.spec.ontology.public import EntropySource, NonDeterminismIntentSource

_MAGNITUDE_ORDER = {
    EntropyMagnitude.LOW: 0,
    EntropyMagnitude.MEDIUM: 1,
    EntropyMagnitude.HIGH: 2,
}


@dataclass(frozen=True)
class NonDeterminismPolicy:
    """Non-determinism policy; misuse breaks governance."""

    spec_version: str
    allowed_sources: tuple[EntropySource, ...]
    allowed_intent_sources: tuple[NonDeterminismIntentSource, ...]
    min_entropy_magnitude: EntropyMagnitude
    max_entropy_magnitude: EntropyMagnitude
    allowed_variance_class: EntropyMagnitude
    policy_id: str = "default"
    require_justification: bool = True

    def validate_intents(self, intents: tuple[NonDeterministicIntent, ...]) -> None:
        """Validate intents against policy; raises on violation."""
        if not intents:
            return
        for intent in intents:
            if intent.source not in self.allowed_intent_sources:
                raise NonDeterminismViolationError(
                    "nondeterminism intent source not allowed by policy"
                )
            if self.require_justification and not intent.justification.strip():
                raise NonDeterminismViolationError(
                    "nondeterminism intent requires justification"
                )
            if (
                _MAGNITUDE_ORDER[intent.min_entropy_magnitude]
                < _MAGNITUDE_ORDER[self.min_entropy_magnitude]
            ):
                raise NonDeterminismViolationError(
                    "intent min entropy below policy minimum"
                )
            if (
                _MAGNITUDE_ORDER[intent.max_entropy_magnitude]
                > _MAGNITUDE_ORDER[self.max_entropy_magnitude]
            ):
                raise NonDeterminismViolationError(
                    "intent max entropy above policy maximum"
                )


__all__ = ["NonDeterminismPolicy"]
