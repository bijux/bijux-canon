# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/model/artifact/retrieved_evidence.py."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_flows.spec.ontology import EvidenceDeterminism
from agentic_flows.spec.ontology.ids import (
    ContentHash,
    ContractID,
    EvidenceID,
    TenantID,
)


@dataclass(frozen=True)
class RetrievedEvidence:
    """Retrieved evidence; misuse breaks verification trust."""

    spec_version: str
    evidence_id: EvidenceID
    tenant_id: TenantID
    determinism: EvidenceDeterminism
    source_uri: str
    content_hash: ContentHash
    score: float
    vector_contract_id: ContractID


__all__ = ["RetrievedEvidence"]
