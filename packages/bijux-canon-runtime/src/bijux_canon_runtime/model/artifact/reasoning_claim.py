# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for model/artifact/reasoning_claim.py."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_runtime.ontology.ids import ClaimID, EvidenceID


@dataclass(frozen=True)
class ReasoningClaim:
    """Reasoning claim; misuse breaks evidence linkage."""

    spec_version: str
    claim_id: ClaimID
    statement: str
    confidence: float
    supported_by: tuple[EvidenceID, ...]


__all__ = ["ReasoningClaim"]
