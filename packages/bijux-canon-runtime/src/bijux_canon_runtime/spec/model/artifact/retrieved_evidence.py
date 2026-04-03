# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for spec/model/artifact/retrieved_evidence.py."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_runtime.spec.ontology import EvidenceDeterminism
from bijux_canon_runtime.spec.ontology.ids import (
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
