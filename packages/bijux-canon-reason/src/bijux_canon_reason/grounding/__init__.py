# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Grounded generation inputs and evidence selection."""

from __future__ import annotations

from bijux_canon_reason.grounding.extractive_synthesis import (
    CredentialFreeSynthesis,
    CredentialFreeSynthesisPolicy,
    CredentialFreeSynthesizer,
    ExtractiveSynthesisPoint,
    SynthesisOutcome,
    SynthesisStyle,
)
from bijux_canon_reason.grounding.evidence_packets import (
    CitationEvidence,
    EvidencePacket,
    EvidencePacketBuilder,
    EvidencePacketError,
    EvidencePacketErrorCode,
    EvidencePacketPolicy,
    EvidenceSelectionDecision,
    EvidenceTrust,
    ImmutableEvidenceLocator,
    OmissionReason,
    PacketCompleteness,
    SelectionDisposition,
    TokenCounter,
    UnicodeLexicalTokenCounter,
)

__all__ = [
    "CitationEvidence",
    "CredentialFreeSynthesis",
    "CredentialFreeSynthesisPolicy",
    "CredentialFreeSynthesizer",
    "EvidencePacket",
    "EvidencePacketBuilder",
    "EvidencePacketError",
    "EvidencePacketErrorCode",
    "EvidencePacketPolicy",
    "EvidenceSelectionDecision",
    "EvidenceTrust",
    "ExtractiveSynthesisPoint",
    "ImmutableEvidenceLocator",
    "OmissionReason",
    "PacketCompleteness",
    "SelectionDisposition",
    "SynthesisOutcome",
    "SynthesisStyle",
    "TokenCounter",
    "UnicodeLexicalTokenCounter",
]
