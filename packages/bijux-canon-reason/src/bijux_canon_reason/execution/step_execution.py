# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass, field

from bijux_canon_reason.core.types import (
    Claim,
    ClaimStatus,
    ClaimType,
    DeriveOutput,
    FinalizeOutput,
    GatherOutput,
    InsufficientEvidenceOutput,
    JsonValue,
    PlanNode,
    ProblemSpec,
    StepOutput,
    SupportKind,
    SupportRef,
    UnderstandOutput,
    VerifyOutput,
)
from bijux_canon_reason.execution.evidence_records import coerce_reasoner_value
from bijux_canon_reason.reasoning.backend import BaselineReasoner


@dataclass
class ExecutionState:
    claims: dict[str, Claim] = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)
    evidence_bytes: dict[str, bytes] = field(default_factory=dict)
    validated_claim_ids: list[str] = field(default_factory=list)
    rejected_claim_ids: list[str] = field(default_factory=list)
    missing_support_claim_ids: list[str] = field(default_factory=list)
    retrieval_provenance: dict[str, JsonValue] = field(default_factory=dict)
    reasoning_meta: dict[str, JsonValue] = field(default_factory=dict)


def build_step_output(
    *,
    node: PlanNode,
    spec: ProblemSpec,
    state: ExecutionState,
    min_supports: int,
) -> StepOutput:
    if node.kind == "understand":
        return UnderstandOutput(
            normalized_question=spec.description.strip(),
            assumptions=[],
        )
    if node.kind == "gather":
        return GatherOutput(
            evidence_ids=list(state.evidence_ids),
            retrieval_queries=[spec.description],
            retrieval_provenance=state.retrieval_provenance,
        )
    if node.kind == "derive":
        return _build_derive_output(spec=spec, state=state, min_supports=min_supports)
    if node.kind == "verify":
        return _build_verify_output(state)
    if node.kind == "finalize":
        return _build_finalize_output(state)
    raise RuntimeError(f"Unknown step kind: {node.kind}")


def _build_derive_output(
    *,
    spec: ProblemSpec,
    state: ExecutionState,
    min_supports: int,
) -> StepOutput:
    ranked_evidence = [
        (evidence_id, state.evidence_bytes.get(evidence_id, b""))
        for evidence_id in state.evidence_ids
    ]
    available = [evidence for evidence in ranked_evidence if evidence[1]]
    if len(available) < min_supports:
        return InsufficientEvidenceOutput(
            retrieved=len(available),
            required=min_supports,
        )

    raw_max = (
        spec.constraints.get("max_citations", min_supports)
        if isinstance(spec.constraints, dict)
        else min_supports
    )
    try:
        max_citations = (
            max(min_supports, int(raw_max))
            if isinstance(raw_max, (int, float, str))
            else min_supports
        )
    except Exception:  # noqa: BLE001
        max_citations = min_supports

    derivation = BaselineReasoner().derive(
        question=spec.description,
        evidence=ranked_evidence,
        max_citations=max_citations,
    )
    supports = [
        SupportRef(
            kind=SupportKind.evidence,
            ref_id=citation.evidence_id,
            span=citation.span,
            snippet_sha256=citation.snippet_sha256,
        )
        for citation in derivation.citations
    ]
    reasoner_payload: dict[str, JsonValue] = {}
    if isinstance(derivation.raw_reasoner, dict):
        for key, value in derivation.raw_reasoner.items():
            reasoner_payload[str(key)] = coerce_reasoner_value(value)

    claim = Claim(
        id="",
        statement=derivation.statement,
        status=ClaimStatus.proposed,
        confidence=0.7 if supports else 0.1,
        supports=supports,
        claim_type=ClaimType.derived,
        structured={
            "reasoner": reasoner_payload,
            "result_sha256": derivation.result_sha256,
        },
    ).with_content_id()
    state.claims[claim.id] = claim
    state.reasoning_meta.update(
        {
            "question": coerce_reasoner_value(spec.description),
            "evidence_ids": [evidence_id for evidence_id, _ in ranked_evidence],
            "result_sha256": coerce_reasoner_value(derivation.result_sha256),
        }
    )
    return DeriveOutput(claim_ids=[claim.id])


def _build_verify_output(state: ExecutionState) -> StepOutput:
    for claim_id, claim in state.claims.items():
        if claim.claim_type == ClaimType.assumed or claim.supports:
            state.validated_claim_ids.append(claim_id)
        else:
            state.missing_support_claim_ids.append(claim_id)
            state.rejected_claim_ids.append(claim_id)
    return VerifyOutput(
        validated_claim_ids=sorted(set(state.validated_claim_ids)),
        rejected_claim_ids=sorted(set(state.rejected_claim_ids)),
        missing_support_claim_ids=sorted(set(state.missing_support_claim_ids)),
    )


def _build_finalize_output(state: ExecutionState) -> StepOutput:
    final_ids = sorted(set(state.validated_claim_ids)) or sorted(state.claims.keys())
    answer = state.claims[final_ids[0]].statement if final_ids else None
    return FinalizeOutput(
        final_claim_ids=final_ids,
        final_answer=answer,
        uncertainty=None if final_ids else "No validated claim",
    )


__all__ = ["ExecutionState", "build_step_output"]
