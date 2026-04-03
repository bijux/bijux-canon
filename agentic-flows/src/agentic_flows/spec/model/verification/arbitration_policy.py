# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/model/verification/arbitration_policy.py."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_flows.spec.ontology import ArbitrationRule


@dataclass(frozen=True)
class ArbitrationPolicy:
    """Arbitration policy record; misuse breaks verification decisions."""

    spec_version: str
    rule: ArbitrationRule
    quorum_threshold: int | None


__all__ = ["ArbitrationPolicy"]
