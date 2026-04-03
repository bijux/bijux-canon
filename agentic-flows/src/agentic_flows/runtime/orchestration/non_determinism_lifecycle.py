# INTERNAL — NOT A PUBLIC EXTENSION POINT
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/orchestration/non_determinism_lifecycle.py."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_flows.runtime.observability.classification.entropy import EntropyLedger
from agentic_flows.spec.model.artifact.entropy_budget import EntropyBudget
from agentic_flows.spec.model.artifact.entropy_usage import EntropyUsage
from agentic_flows.spec.model.artifact.non_determinism_source import (
    NonDeterminismSource,
)
from agentic_flows.spec.model.execution.non_deterministic_intent import (
    NonDeterministicIntent,
)
from agentic_flows.spec.ontology import EntropyExhaustionAction, EntropyMagnitude
from agentic_flows.spec.ontology.ids import TenantID
from agentic_flows.spec.ontology.public import EntropySource


@dataclass(frozen=True)
class NonDeterminismVerdict:
    """Verdict metadata for nondeterminism; misuse breaks auditability."""

    entropy_exhausted: bool
    entropy_exhaustion_action: EntropyExhaustionAction | None
    non_certifiable: bool


class NonDeterminismLifecycle:
    """Orchestrate non-determinism intent, usage, and final verdicts."""

    def __init__(
        self,
        *,
        budget: EntropyBudget | None,
        intents: tuple[NonDeterministicIntent, ...],
        allowed_variance_class: EntropyMagnitude | None,
    ) -> None:
        """Register intent and initialize the ledger."""
        self._intents = intents
        self._ledger = EntropyLedger(
            budget,
            intents=intents,
            allowed_variance_class=allowed_variance_class,
        )

    def register_intents(self) -> tuple[NonDeterministicIntent, ...]:
        """Expose registered intents for auditing."""
        return self._intents

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
        """Track entropy usage and enforce intent/budget rules."""
        self._ledger.record(
            tenant_id=tenant_id,
            source=source,
            magnitude=magnitude,
            description=description,
            step_index=step_index,
            nondeterminism_source=nondeterminism_source,
        )

    def seed(self, records: tuple[EntropyUsage, ...]) -> None:
        """Seed with previously persisted entropy usage."""
        self._ledger.seed(records)

    def usage(self) -> tuple[EntropyUsage, ...]:
        """Return recorded entropy usage."""
        return self._ledger.usage()

    def verdict(self) -> NonDeterminismVerdict:
        """Emit final verdict metadata for persistence."""
        exhausted = self._ledger.exhausted()
        action = self._ledger.exhaustion_action()
        non_certifiable = (
            exhausted and action is EntropyExhaustionAction.MARK_NON_CERTIFIABLE
        )
        return NonDeterminismVerdict(
            entropy_exhausted=exhausted,
            entropy_exhaustion_action=action,
            non_certifiable=non_certifiable,
        )


__all__ = ["NonDeterminismLifecycle", "NonDeterminismVerdict"]
