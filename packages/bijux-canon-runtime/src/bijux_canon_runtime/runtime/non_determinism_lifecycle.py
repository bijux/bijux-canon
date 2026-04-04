# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Runtime-owned lifecycle for non-determinism intent, usage, and verdicts."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_runtime.model.artifact.entropy_budget import EntropyBudget
from bijux_canon_runtime.model.artifact.entropy_usage import EntropyUsage
from bijux_canon_runtime.model.artifact.non_determinism_source import (
    NonDeterminismSource,
)
from bijux_canon_runtime.model.execution.non_deterministic_intent import (
    NonDeterministicIntent,
)
from bijux_canon_runtime.observability.classification.entropy import EntropyLedger
from bijux_canon_runtime.ontology import EntropyExhaustionAction, EntropyMagnitude
from bijux_canon_runtime.ontology.ids import TenantID
from bijux_canon_runtime.ontology.public import EntropySource


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
        """Track entropy usage and enforce intent and budget rules."""
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
