# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/model/artifact/non_determinism_source.py."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_flows.spec.ontology.ids import FlowID, StepID
from agentic_flows.spec.ontology.public import EntropySource


@dataclass(frozen=True)
class NonDeterminismSource:
    """Nondeterminism source record; misuse breaks entropy audit."""

    source: EntropySource
    authorized: bool
    scope: StepID | FlowID


__all__ = ["NonDeterminismSource"]
