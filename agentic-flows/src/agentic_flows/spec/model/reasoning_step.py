# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/model/reasoning_step.py."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_flows.spec.ontology.ids import ClaimID, StepID


@dataclass(frozen=True)
class ReasoningStep:
    """Reasoning step; misuse breaks reasoning sequence."""

    spec_version: str
    step_id: StepID
    input_claims: tuple[ClaimID, ...]
    output_claims: tuple[ClaimID, ...]
    method: str


__all__ = ["ReasoningStep"]
