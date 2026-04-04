from __future__ import annotations

from bijux_canon_runtime.model.artifact.reasoning_claim import ReasoningClaim
from bijux_canon_runtime.model.reasoning.bundle import ReasoningBundle
from bijux_canon_runtime.model.reasoning.step import ReasoningStep
from bijux_canon_runtime.ontology.ids import (
    AgentID,
    BundleID,
    ClaimID,
    EvidenceID,
    StepID,
)
from bijux_canon_runtime.verification.contradiction_support import (
    detect_contradictions,
)


def _bundle(*claims: ReasoningClaim) -> ReasoningBundle:
    return ReasoningBundle(
        spec_version="v1",
        bundle_id=BundleID("bundle"),
        claims=claims,
        steps=(
            ReasoningStep(
                spec_version="v1",
                step_id=StepID("step"),
                input_claims=(),
                output_claims=tuple(claim.claim_id for claim in claims),
                method="deduction",
            ),
        ),
        evidence_ids=(EvidenceID("evidence-1"),),
        producer_agent_id=AgentID("agent"),
    )


def _claim(claim_id: str, statement: str, confidence: float) -> ReasoningClaim:
    return ReasoningClaim(
        spec_version="v1",
        claim_id=ClaimID(claim_id),
        statement=statement,
        supported_by=(EvidenceID("evidence-1"),),
        confidence=confidence,
    )


def test_detect_contradictions_flags_direct_contradictions() -> None:
    violations = detect_contradictions(
        [
            _bundle(
                _claim("claim-1", "Sky is blue", 0.9),
                _claim("claim-2", "not sky is blue", 0.8),
            )
        ]
    )

    assert "direct_contradiction" in violations


def test_detect_contradictions_flags_weakened_restatement() -> None:
    violations = detect_contradictions(
        [
            _bundle(
                _claim("claim-1", "Sky is blue", 0.9),
                _claim("claim-2", "sky is blue", 0.4),
            )
        ]
    )

    assert "weakened_restatement" in violations
