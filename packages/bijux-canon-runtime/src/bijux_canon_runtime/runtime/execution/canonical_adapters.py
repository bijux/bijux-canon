# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Versioned adapters for installed canonical package application services."""

from __future__ import annotations

import contextlib
import hashlib
import json
from pathlib import Path

from bijux_canon_agent.application.execution_service import run_offline_agent
from bijux_canon_index.core.contracts.execution_abi import assert_execution_abi
from bijux_canon_ingest.application.querying import retrieve
from bijux_canon_reason.application.run_workflow import run_app
from bijux_canon_reason.core.types import ProblemSpec, TraceEventKind
from bijux_canon_runtime.core.errors import ConfigurationError, ExecutionFailure
from bijux_canon_runtime.model.artifact.artifact import Artifact
from bijux_canon_runtime.model.artifact.reasoning_claim import ReasoningClaim
from bijux_canon_runtime.model.artifact.retrieved_evidence import RetrievedEvidence
from bijux_canon_runtime.model.reasoning.bundle import ReasoningBundle
from bijux_canon_runtime.model.reasoning.step import ReasoningStep
from bijux_canon_runtime.ontology import ArtifactType
from bijux_canon_runtime.ontology.ids import (
    AgentID,
    BundleID,
    ClaimID,
    ContractID,
    EvidenceID,
    StepID,
)


def _canonical_json(value: object) -> str:
    """Serialize adapter records deterministically across package boundaries."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


class CanonicalAgentAdapterV1:
    """Translate runtime agent requests to the canonical offline agent service."""

    adapter_id = "bijux-canon-agent:application:offline:v1"

    def __init__(self, *, working_root: Path) -> None:
        """Bind the explicit filesystem authority used for agent artifacts."""
        self._working_root = working_root

    def run(
        self,
        *,
        agent_id: AgentID,
        seed: int,
        inputs_fingerprint: str,
        declared_outputs: tuple[str, ...],
        evidence: list[RetrievedEvidence],
    ) -> list[dict[str, object]]:
        """Run the installed deterministic service and normalize its artifact."""
        input_record = {
            "adapter_id": self.adapter_id,
            "agent_id": str(agent_id),
            "seed": seed,
            "inputs_fingerprint": str(inputs_fingerprint),
            "evidence": [
                {
                    "evidence_id": str(item.evidence_id),
                    "content_hash": str(item.content_hash),
                    "source_uri": item.source_uri,
                }
                for item in evidence
            ],
        }
        context_id = hashlib.sha256(
            _canonical_json(input_record).encode("utf-8")
        ).hexdigest()
        outcome = run_offline_agent(
            context_id=context_id,
            text=_canonical_json(input_record),
            task_goal="Summarize the supplied evidence record.",
            working_root=self._working_root,
        )
        if not outcome.success or outcome.result is None:
            raise ExecutionFailure(
                outcome.error_message or "canonical agent execution failed"
            )
        content = _canonical_json(outcome.result)
        artifact_id = hashlib.sha256(content.encode("utf-8")).hexdigest()
        artifact_type = ArtifactType.AGENT_INVOCATION.value
        if declared_outputs:
            with contextlib.suppress(ValueError):
                artifact_type = ArtifactType(declared_outputs[0]).value
        return [
            {
                "artifact_id": f"agent-{artifact_id}",
                "artifact_type": artifact_type,
                "content": content,
                "parent_artifacts": [],
            }
        ]


class CanonicalRetrievalAdapterV1:
    """Translate runtime retrieval requests to the persisted ingest query service."""

    adapter_id = "bijux-canon-ingest:application:querying:v1"

    def __init__(self, *, index_path: Path | None) -> None:
        """Bind the persisted index selected by runtime configuration."""
        self._index_path = index_path

    def retrieve(
        self,
        *,
        query: str,
        top_k: int,
        scope: str,
        vector_contract_id: ContractID,
    ) -> list[dict[str, object]]:
        """Retrieve canonical candidates and preserve exact content for hashing."""
        if self._index_path is None:
            raise ConfigurationError(
                "BIJUX_CANON_RUNTIME_RETRIEVAL_INDEX_PATH is required for retrieval"
            )
        candidates = retrieve(
            index_path=self._index_path,
            query=query,
            top_k=top_k,
        )
        return [
            {
                "evidence_id": candidate.chunk_id,
                "determinism": "deterministic",
                "source_uri": str(
                    candidate.metadata.get(
                        "source_uri",
                        f"document:{candidate.doc_id}#chunk={candidate.chunk_id}",
                    )
                ),
                "content": candidate.text,
                "score": candidate.score,
                "scope": scope,
                "vector_contract_id": str(vector_contract_id),
            }
            for candidate in candidates
        ]


class CanonicalReasonAdapterV1:
    """Translate runtime evidence records through the canonical reason service."""

    adapter_id = "bijux-canon-reason:application:run:v1"

    def reason(
        self,
        *,
        agent_outputs: list[Artifact],
        evidence: list[RetrievedEvidence],
        seed: int,
    ) -> ReasoningBundle:
        """Execute canonical reasoning and map its typed trace to runtime records."""
        description = _canonical_json(
            {
                "adapter_id": self.adapter_id,
                "agent_artifacts": [
                    {
                        "artifact_id": str(item.artifact_id),
                        "content_hash": str(item.content_hash),
                    }
                    for item in agent_outputs
                ],
                "evidence": [
                    {
                        "evidence_id": str(item.evidence_id),
                        "content_hash": str(item.content_hash),
                        "source_uri": item.source_uri,
                    }
                    for item in evidence
                ],
            }
        )
        result = run_app(
            spec=ProblemSpec(description=description),
            preset="default",
            seed=seed,
        )
        emitted = [
            event
            for event in result.trace.events
            if event.kind is TraceEventKind.claim_emitted
        ]
        claims = tuple(
            ReasoningClaim(
                spec_version="v1",
                claim_id=ClaimID(event.claim.id),
                statement=event.claim.statement,
                confidence=event.claim.confidence,
                supported_by=tuple(
                    EvidenceID(support.ref_id)
                    for support in event.claim.supports
                    if support.kind.value == "evidence"
                ),
            )
            for event in emitted
        )
        steps = tuple(
            ReasoningStep(
                spec_version="v1",
                step_id=StepID(event.step_id),
                input_claims=(),
                output_claims=(ClaimID(event.claim.id),),
                method=self.adapter_id,
            )
            for event in emitted
        )
        trace_identity = (
            result.trace.id
            or hashlib.sha256(
                _canonical_json(
                    [event.model_dump(mode="json") for event in result.trace.events]
                ).encode("utf-8")
            ).hexdigest()
        )
        return ReasoningBundle(
            spec_version="v1",
            bundle_id=BundleID(trace_identity),
            claims=claims,
            steps=steps,
            evidence_ids=tuple(item.evidence_id for item in evidence),
            producer_agent_id=AgentID(self.adapter_id),
        )


class CanonicalVectorContractAdapterV1:
    """Bind runtime contract checks to the canonical index execution ABI."""

    adapter_id = "bijux-canon-index:execution-abi:v1"

    def __init__(self) -> None:
        """Fail construction when the installed index ABI is not valid."""
        assert_execution_abi()

    def enforce(
        self, contract_id: ContractID, evidence: list[RetrievedEvidence]
    ) -> bool:
        """Require nonempty evidence bound to exactly the requested contract."""
        return bool(evidence) and all(
            item.vector_contract_id == contract_id for item in evidence
        )


__all__ = [
    "CanonicalAgentAdapterV1",
    "CanonicalReasonAdapterV1",
    "CanonicalRetrievalAdapterV1",
    "CanonicalVectorContractAdapterV1",
]
