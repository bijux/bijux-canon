# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/observability/classification/entropy.py."""

from __future__ import annotations

from agentic_flows.core.errors import NonDeterminismViolationError
from agentic_flows.spec.model.artifact.entropy_budget import (
    EntropyBudget,
    EntropyBudgetSlice,
)
from agentic_flows.spec.model.artifact.entropy_usage import EntropyUsage
from agentic_flows.spec.model.artifact.non_determinism_source import (
    NonDeterminismSource,
)
from agentic_flows.spec.model.execution.non_deterministic_intent import (
    NonDeterministicIntent,
)
from agentic_flows.spec.ontology import EntropyExhaustionAction, EntropyMagnitude
from agentic_flows.spec.ontology.ids import TenantID
from agentic_flows.spec.ontology.public import (
    EntropySource,
    NonDeterminismIntentSource,
)

_MAGNITUDE_ORDER = {
    EntropyMagnitude.LOW: 0,
    EntropyMagnitude.MEDIUM: 1,
    EntropyMagnitude.HIGH: 2,
}


class EntropyLedger:
    """Entropy ledger; misuse breaks entropy accounting."""

    def __init__(
        self,
        budget: EntropyBudget | None,
        *,
        intents: tuple[NonDeterministicIntent, ...],
        allowed_variance_class: EntropyMagnitude | None,
    ) -> None:
        """Internal helper; not part of the public API."""
        self._budget = budget
        self._intents = intents
        self._allowed_variance_class = allowed_variance_class
        self._records: list[EntropyUsage] = []
        self._exhausted = False
        self._exhaustion_action: EntropyExhaustionAction | None = None

    def record(
        self,
        *,
        tenant_id: TenantID,
        source: EntropySource,
        magnitude: EntropyMagnitude,
        description: str,
        step_index: int | None,
        nondeterminism_source: NonDeterminismSource,
    ) -> None:
        """Execute record and enforce its contract."""
        if self._budget is None:
            raise NonDeterminismViolationError(
                "entropy budget must be declared before entropy is used"
            )
        if not self._intents:
            raise NonDeterminismViolationError(
                "entropy used without declared non-determinism intent"
            )
        if self._allowed_variance_class is not None and (
            _MAGNITUDE_ORDER[magnitude] > _MAGNITUDE_ORDER[self._allowed_variance_class]
        ):
            raise NonDeterminismViolationError(
                "entropy magnitude exceeds allowed variance class"
            )
        self._assert_intent(source=source, magnitude=magnitude)
        slice_budget = self._budget_slice(source)
        if source not in self._budget.allowed_sources:
            raise NonDeterminismViolationError("entropy source not allowed by policy")
        min_magnitude = (
            slice_budget.min_magnitude if slice_budget else self._budget.min_magnitude
        )
        max_magnitude = (
            slice_budget.max_magnitude if slice_budget else self._budget.max_magnitude
        )
        if _MAGNITUDE_ORDER[magnitude] < _MAGNITUDE_ORDER[min_magnitude]:
            raise NonDeterminismViolationError(
                "entropy magnitude below declared budget minimum"
            )
        if _MAGNITUDE_ORDER[magnitude] > _MAGNITUDE_ORDER[max_magnitude]:
            action = (
                slice_budget.exhaustion_action
                if slice_budget and slice_budget.exhaustion_action is not None
                else self._budget.exhaustion_action
            )
            self._exhausted = True
            self._exhaustion_action = action
            if action is EntropyExhaustionAction.HALT:
                raise NonDeterminismViolationError(
                    "entropy magnitude exceeds declared budget"
                )
        self._records.append(
            EntropyUsage(
                spec_version="v1",
                tenant_id=tenant_id,
                source=source,
                magnitude=magnitude,
                description=description,
                step_index=step_index,
                nondeterminism_source=nondeterminism_source,
            )
        )

    def seed(self, records: tuple[EntropyUsage, ...]) -> None:
        """Execute seed and enforce its contract."""
        self._records.extend(records)

    def usage(self) -> tuple[EntropyUsage, ...]:
        """Execute usage and enforce its contract."""
        return tuple(self._records)

    def exhausted(self) -> bool:
        """Execute exhausted and enforce its contract."""
        return self._exhausted

    def exhaustion_action(self) -> EntropyExhaustionAction | None:
        """Execute exhaustion_action and enforce its contract."""
        if not self._budget:
            return None
        return self._exhaustion_action or self._budget.exhaustion_action

    def _assert_intent(
        self, *, source: EntropySource, magnitude: EntropyMagnitude
    ) -> None:
        intent_source = _intent_source_for_entropy(source)
        for intent in self._intents:
            if intent.source is not intent_source:
                continue
            if (
                _MAGNITUDE_ORDER[magnitude]
                < _MAGNITUDE_ORDER[intent.min_entropy_magnitude]
            ):
                continue
            if (
                _MAGNITUDE_ORDER[magnitude]
                > _MAGNITUDE_ORDER[intent.max_entropy_magnitude]
            ):
                continue
            return
        raise NonDeterminismViolationError(
            "entropy magnitude/source not declared in non-determinism intent"
        )

    def _budget_slice(self, source: EntropySource) -> EntropyBudgetSlice | None:
        if not self._budget:
            return None
        for entry in self._budget.per_source:
            if entry.source is source:
                return entry
        return None


def _intent_source_for_entropy(source: EntropySource) -> NonDeterminismIntentSource:
    mapping = {
        EntropySource.SEEDED_RNG: NonDeterminismIntentSource.LLM,
        EntropySource.DATA: NonDeterminismIntentSource.RETRIEVAL,
        EntropySource.HUMAN_INPUT: NonDeterminismIntentSource.HUMAN,
        EntropySource.EXTERNAL_ORACLE: NonDeterminismIntentSource.EXTERNAL,
    }
    return mapping[source]


__all__ = ["EntropyLedger"]
