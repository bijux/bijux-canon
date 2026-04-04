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
from bijux_canon_reason.reasoning.extractive import Derivation


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
    ranked_evidence = _ranked_evidence(state)
    available = _available_evidence(ranked_evidence)
    if len(available) < min_supports:
        return InsufficientEvidenceOutput(
            retrieved=len(available),
            required=min_supports,
        )

    derivation = BaselineReasoner().derive(
        question=spec.description,
        evidence=ranked_evidence,
        max_citations=_resolve_max_citations(spec=spec, min_supports=min_supports),
    )
    claim = _build_derived_claim(derivation)
    _record_derivation(
        state=state,
        spec=spec,
        ranked_evidence=ranked_evidence,
        claim=claim,
        result_sha256=derivation.result_sha256,
    )
    return DeriveOutput(claim_ids=[claim.id])


def _build_verify_output(state: ExecutionState) -> StepOutput:
    _apply_verification_outcomes(state)
    return VerifyOutput(
        validated_claim_ids=sorted(set(state.validated_claim_ids)),
        rejected_claim_ids=sorted(set(state.rejected_claim_ids)),
        missing_support_claim_ids=sorted(set(state.missing_support_claim_ids)),
    )


def _build_finalize_output(state: ExecutionState) -> StepOutput:
    final_ids = _final_claim_ids(state)
    answer = state.claims[final_ids[0]].statement if final_ids else None
    return FinalizeOutput(
        final_claim_ids=final_ids,
        final_answer=answer,
        uncertainty=None if final_ids else "No validated claim",
    )


def _ranked_evidence(state: ExecutionState) -> list[tuple[str, bytes]]:
    return [
        (evidence_id, state.evidence_bytes.get(evidence_id, b""))
        for evidence_id in state.evidence_ids
    ]


def _available_evidence(ranked_evidence: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
    return [evidence for evidence in ranked_evidence if evidence[1]]


def _resolve_max_citations(*, spec: ProblemSpec, min_supports: int) -> int:
    raw_max = (
        spec.constraints.get("max_citations", min_supports)
        if isinstance(spec.constraints, dict)
        else min_supports
    )
    try:
        if isinstance(raw_max, (int, float, str)):
            return max(min_supports, int(raw_max))
    except Exception:  # noqa: BLE001
        pass
    return min_supports


def _build_derived_claim(derivation: Derivation) -> Claim:
    supports = [
        SupportRef(
            kind=SupportKind.evidence,
            ref_id=citation.evidence_id,
            span=citation.span,
            snippet_sha256=citation.snippet_sha256,
        )
        for citation in derivation.citations
    ]
    return Claim(
        id="",
        statement=derivation.statement,
        status=ClaimStatus.proposed,
        confidence=0.7 if supports else 0.1,
        supports=supports,
        claim_type=ClaimType.derived,
        structured={
            "reasoner": _reasoner_payload(derivation.raw_reasoner),
            "result_sha256": derivation.result_sha256,
        },
    ).with_content_id()


def _reasoner_payload(raw_reasoner: object) -> dict[str, JsonValue]:
    if not isinstance(raw_reasoner, dict):
        return {}
    payload: dict[str, JsonValue] = {}
    for key, value in raw_reasoner.items():
        payload[str(key)] = coerce_reasoner_value(value)
    return payload


def _record_derivation(
    *,
    state: ExecutionState,
    spec: ProblemSpec,
    ranked_evidence: list[tuple[str, bytes]],
    claim: Claim,
    result_sha256: str,
) -> None:
    state.claims[claim.id] = claim
    state.reasoning_meta.update(
        {
            "question": coerce_reasoner_value(spec.description),
            "evidence_ids": [evidence_id for evidence_id, _ in ranked_evidence],
            "result_sha256": coerce_reasoner_value(result_sha256),
        }
    )


def _apply_verification_outcomes(state: ExecutionState) -> None:
    for claim_id, claim in state.claims.items():
        if claim.claim_type == ClaimType.assumed or claim.supports:
            state.validated_claim_ids.append(claim_id)
            continue
        state.missing_support_claim_ids.append(claim_id)
        state.rejected_claim_ids.append(claim_id)


def _final_claim_ids(state: ExecutionState) -> list[str]:
    return sorted(set(state.validated_claim_ids)) or sorted(state.claims.keys())


__all__ = ["ExecutionState", "build_step_output"]
