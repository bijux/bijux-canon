# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for spec/model/artifact/entropy_usage.py."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_runtime.spec.model.artifact.non_determinism_source import (
    NonDeterminismSource,
)
from bijux_canon_runtime.spec.ontology import EntropyMagnitude
from bijux_canon_runtime.spec.ontology.ids import TenantID
from bijux_canon_runtime.spec.ontology.public import EntropySource


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
