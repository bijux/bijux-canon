# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for model/artifact/non_determinism_source.py."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_runtime.ontology.ids import FlowID, StepID
from bijux_canon_runtime.ontology.public import EntropySource


@dataclass(frozen=True)
class NonDeterminismSource:
    """Nondeterminism source record; misuse breaks entropy audit."""

    source: EntropySource
    authorized: bool
    scope: StepID | FlowID


__all__ = ["NonDeterminismSource"]
