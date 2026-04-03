# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/model/reasoning_bundle.py."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_flows.spec.model.artifact.reasoning_claim import ReasoningClaim
from agentic_flows.spec.model.reasoning_step import ReasoningStep
from agentic_flows.spec.ontology.ids import AgentID, BundleID, EvidenceID


@dataclass(frozen=True)
class ReasoningBundle:
    """Reasoning bundle; misuse breaks claim verification."""

    spec_version: str
    bundle_id: BundleID
    claims: tuple[ReasoningClaim, ...]
    steps: tuple[ReasoningStep, ...]
    evidence_ids: tuple[EvidenceID, ...]
    producer_agent_id: AgentID


__all__ = ["ReasoningBundle"]
