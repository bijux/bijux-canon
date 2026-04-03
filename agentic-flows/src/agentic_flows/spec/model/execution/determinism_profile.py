# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/model/execution/determinism_profile.py."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_flows.spec.model.artifact.entropy_budget import EntropyBudgetSlice
from agentic_flows.spec.ontology import EntropyMagnitude, EntropySeverity
from agentic_flows.spec.ontology.public import EntropySource, ReplayAcceptability


@dataclass(frozen=True)
class EntropySourceProfile:
    """Per-source entropy profile; misuse breaks auditability."""

    source: EntropySource
    severity: EntropySeverity
    observed_magnitude: EntropyMagnitude | None
    budget_slice: EntropyBudgetSlice | None = None


@dataclass(frozen=True)
class DeterminismProfile:
    """Structured determinism profile; misuse breaks auditability."""

    spec_version: str
    entropy_magnitude: EntropyMagnitude | None
    entropy_sources: tuple[EntropySource, ...]
    source_profiles: tuple[EntropySourceProfile, ...]
    replay_acceptability: ReplayAcceptability
    confidence_decay: float


__all__ = ["DeterminismProfile", "EntropySourceProfile"]
