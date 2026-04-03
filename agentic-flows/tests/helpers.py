# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from agentic_flows.spec.model.artifact.artifact import Artifact
from agentic_flows.spec.model.artifact.retrieved_evidence import RetrievedEvidence


def build_claim_statement(
    agent_outputs: list[Artifact],
    evidence: list[RetrievedEvidence],
) -> str:
    parts: list[str] = []
    if evidence:
        parts.append(f"evidence_id={evidence[0].evidence_id}")
        parts.append(f"evidence_hash={evidence[0].content_hash}")
    if agent_outputs:
        parts.append(f"artifact_hash={agent_outputs[0].content_hash}")
    return " ".join(parts)
