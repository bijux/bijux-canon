# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for model/execution/non_deterministic_intent.py."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_runtime.ontology import EntropyMagnitude
from bijux_canon_runtime.ontology.public import NonDeterminismIntentSource


@dataclass(frozen=True)
class NonDeterministicIntent:
    """Declared nondeterminism intent; misuse breaks governance."""

    spec_version: str
    source: NonDeterminismIntentSource
    min_entropy_magnitude: EntropyMagnitude
    max_entropy_magnitude: EntropyMagnitude
    justification: str


__all__ = ["NonDeterministicIntent"]
