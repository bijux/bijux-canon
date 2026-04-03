# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/model/artifact/entropy_budget.py."""

from __future__ import annotations

from dataclasses import dataclass, field

from agentic_flows.spec.ontology import EntropyExhaustionAction, EntropyMagnitude
from agentic_flows.spec.ontology.public import EntropySource


@dataclass(frozen=True)
class EntropyBudgetSlice:
    """Entropy budget slice per source; misuse breaks enforcement."""

    source: EntropySource
    min_magnitude: EntropyMagnitude
    max_magnitude: EntropyMagnitude
    exhaustion_action: EntropyExhaustionAction | None = None


@dataclass(frozen=True)
class EntropyBudget:
    """Entropy budget; misuse breaks entropy enforcement."""

    spec_version: str
    allowed_sources: tuple[EntropySource, ...]
    max_magnitude: EntropyMagnitude
    min_magnitude: EntropyMagnitude = EntropyMagnitude.LOW
    exhaustion_action: EntropyExhaustionAction = EntropyExhaustionAction.HALT
    per_source: tuple[EntropyBudgetSlice, ...] = field(default_factory=tuple)


__all__ = ["EntropyBudget", "EntropyBudgetSlice"]
