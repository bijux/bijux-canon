# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/model/artifact/entropy_usage.py."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_flows.spec.model.artifact.non_determinism_source import (
    NonDeterminismSource,
)
from agentic_flows.spec.ontology import EntropyMagnitude
from agentic_flows.spec.ontology.ids import TenantID
from agentic_flows.spec.ontology.public import EntropySource


@dataclass(frozen=True)
class EntropyUsage:
    """Entropy usage record; misuse breaks auditability."""

    spec_version: str
    tenant_id: TenantID
    source: EntropySource
    magnitude: EntropyMagnitude
    description: str
    step_index: int | None
    nondeterminism_source: NonDeterminismSource


__all__ = ["EntropyUsage"]
