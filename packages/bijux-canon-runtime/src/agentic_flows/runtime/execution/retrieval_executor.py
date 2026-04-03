# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/execution/retrieval_executor.py."""

from __future__ import annotations

import hashlib
from typing import Any

import bijux_rag
import bijux_vex

from agentic_flows.runtime.context import ExecutionContext
from agentic_flows.spec.model.artifact.non_determinism_source import (
    NonDeterminismSource,
)
from agentic_flows.spec.model.artifact.retrieved_evidence import RetrievedEvidence
from agentic_flows.spec.model.execution.resolved_step import ResolvedStep
from agentic_flows.spec.ontology import (
    EntropyMagnitude,
    EvidenceDeterminism,
)
from agentic_flows.spec.ontology.ids import (
    ContentHash,
    ContractID,
    EvidenceID,
    StepID,
    TenantID,
)
from agentic_flows.spec.ontology.public import EntropySource


class RetrievalExecutor:
    """Behavioral contract for RetrievalExecutor."""

    def execute(
        self, step: ResolvedStep, context: ExecutionContext
    ) -> list[RetrievedEvidence]:
        """Execute execute and enforce its contract."""
        request = step.retrieval_request
        if request is None:
            context.record_evidence(step.step_index, [])
            return []
        if not hasattr(bijux_rag, "retrieve"):
            raise RuntimeError("bijux_rag.retrieve is required for retrieval")
        if not hasattr(bijux_vex, "enforce_contract"):
            raise RuntimeError("bijux_vex.enforce_contract is required for enforcement")

        raw_evidence = bijux_rag.retrieve(
            query=request.query,
            top_k=request.top_k,
            scope=request.scope,
            vector_contract_id=request.vector_contract_id,
        )

        evidence = self._normalize_evidence(raw_evidence, tenant_id=context.tenant_id)
        if not evidence:
            raise ValueError("retrieval returned no evidence")

        if any(
            item.vector_contract_id != request.vector_contract_id for item in evidence
        ):
            raise ValueError("retrieval evidence vector contract mismatch")

        if not bijux_vex.enforce_contract(request.vector_contract_id, evidence):
            raise ValueError("retrieval evidence failed vector contract enforcement")

        if any(
            item.determinism != EvidenceDeterminism.DETERMINISTIC for item in evidence
        ):
            magnitude = EntropyMagnitude.MEDIUM
            if any(
                item.determinism == EvidenceDeterminism.EXTERNAL for item in evidence
            ):
                magnitude = EntropyMagnitude.HIGH
            context.record_entropy(
                source=EntropySource.DATA,
                magnitude=magnitude,
                description="retrieval evidence determinism",
                step_index=step.step_index,
                nondeterminism_source=NonDeterminismSource(
                    source=EntropySource.DATA,
                    authorized=True,
                    scope=StepID(str(step.step_index)),
                ),
            )
        context.record_evidence(step.step_index, evidence)
        return evidence

    def _normalize_evidence(
        self, raw: Any, *, tenant_id: TenantID
    ) -> list[RetrievedEvidence]:
        """Internal helper; not part of the public API."""
        if not isinstance(raw, list):
            raise ValueError("retrieval results must be a list")

        evidence: list[RetrievedEvidence] = []
        for entry in raw:
            if not isinstance(entry, dict):
                raise ValueError("retrieval evidence must be dict entries")
            if (
                "evidence_id" not in entry
                or "source_uri" not in entry
                or "content" not in entry
                or "determinism" not in entry
                or "vector_contract_id" not in entry
            ):
                raise ValueError("retrieval evidence missing required fields")
            content_hash = ContentHash(self._hash_content(entry["content"]))
            try:
                determinism = EvidenceDeterminism(str(entry["determinism"]))
            except ValueError as exc:
                raise ValueError("retrieval evidence determinism is invalid") from exc
            evidence.append(
                RetrievedEvidence(
                    spec_version="v1",
                    evidence_id=EvidenceID(str(entry["evidence_id"])),
                    tenant_id=tenant_id,
                    determinism=determinism,
                    source_uri=str(entry["source_uri"]),
                    content_hash=content_hash,
                    score=float(entry.get("score", 0.0)),
                    vector_contract_id=ContractID(str(entry["vector_contract_id"])),
                )
            )
        return evidence

    @staticmethod
    def _hash_content(content: Any) -> str:
        """Internal helper; not part of the public API."""
        payload = str(content).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
