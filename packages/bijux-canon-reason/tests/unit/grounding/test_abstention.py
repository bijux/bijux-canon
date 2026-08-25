# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Calibrated admission and actionable abstention tests."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json

from pydantic import ValidationError
import pytest

from bijux_canon_reason.grounding import (
    AtomicClaim,
    AtomicClaimNormalizer,
    CalibratedAbstentionPolicy,
    CitationEvidence,
    CitationSourceDescriptor,
    CitationVerificationPolicy,
    CitationVerificationReport,
    ClaimCitationLink,
    ClaimCitationLinker,
    ClaimCitationSet,
    CredentialFreeSynthesizer,
    DeterministicCitationVerifier,
    EntailmentVerdict,
    EvidenceGapCode,
    EvidencePacketBuilder,
    EvidencePacketPolicy,
    GroundingAdmissionDecision,
    GroundingAdmissionOutcome,
    GroundingAdmissionService,
    GroundingEvidenceState,
    GroundingRequestStatus,
    ImmutableEvidenceLocator,
    JsonHttpResponse,
    NormalizedClaimSet,
    OpenAICompatibleStructuredSynthesizer,
    PacketCompleteness,
    RetrievalEvidenceStatus,
    StructuredEntailmentDecision,
    StructuredEntailmentVerifier,
    StructuredProviderConfiguration,
    VexEvidenceStatus,
)


def test_verified_conservative_projection_has_full_admission_confidence() -> None:
    claims, citations, report = _pipeline(
        (
            (
                "Part C denotes the dense part within the otic capsule.",
                (
                    "Three regions were sampled: trabecular bone (part A), cortical "
                    "bone (part B), and the dense part within the otic capsule (part C)."
                ),
            ),
        )
    )

    decision = GroundingAdmissionService().decide(
        claim_set=claims,
        citation_set=citations,
        verification_report=report,
    )

    assert report.claims[0].assessments[0].rationale_code == (
        "claim_is_verified_conservative_projection"
    )
    assert decision.outcome is GroundingAdmissionOutcome.admitted
    assert decision.minimum_support_confidence == 1.0


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _artifact(value: str) -> str:
    return f"sha256:{_sha(value)}"


class _Transport:
    def __init__(self, candidate: Mapping[str, object]) -> None:
        self._candidate = candidate

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: bytes,
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> JsonHttpResponse:
        del url, headers, body, timeout_seconds, max_response_bytes
        envelope = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(self._candidate),
                    }
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10},
        }
        return JsonHttpResponse(200, json.dumps(envelope).encode(), 1, "request")


def _pipeline(
    pairs: tuple[tuple[str, str], ...],
    *,
    verifier: StructuredEntailmentVerifier | None = None,
    verification_policy: CitationVerificationPolicy | None = None,
) -> tuple[NormalizedClaimSet, ClaimCitationSet, CitationVerificationReport]:
    evidence_items = []
    sources = []
    candidate_claims = []
    for ordinal, (claim, exact_text) in enumerate(pairs, start=1):
        source_id = f"source-{ordinal}"
        source_content = f"Immutable source {ordinal}: {exact_text}"
        source_uri = f"https://doi.org/10.1000/source-{ordinal}"
        evidence = CitationEvidence(
            artifact_id=_artifact(f"evidence:{ordinal}:{exact_text}"),
            chunk_artifact_id=_artifact(f"chunk:{ordinal}:{exact_text}"),
            retrieval_artifact_id=_artifact("retrieval"),
            document_id=f"document-{ordinal}",
            source_id=source_id,
            section_path=("results",),
            locator=ImmutableEvidenceLocator(
                artifact_id=_artifact(f"locator:{ordinal}:{exact_text}"),
                source_artifact_id=_artifact(source_content),
                source_uri=source_uri,
                source_content_sha256=_sha(source_content),
                scheme="unicode-code-point",
                selectors=(("char_start", 20), ("char_end", 20 + len(exact_text))),
            ),
            exact_text=exact_text,
            exact_text_sha256=_sha(exact_text),
            rank=ordinal,
            relevance_score=1.0 / ordinal,
        )
        evidence_items.append(evidence)
        sources.append(
            CitationSourceDescriptor.create(
                source_id=source_id,
                title=f"Durable source {ordinal}",
                canonical_uri=source_uri,
                doi=f"10.1000/source-{ordinal}",
                source_content_sha256=evidence.locator.source_content_sha256,
            )
        )
        candidate_claims.append(
            {
                "statement": claim,
                "citation_evidence_artifact_ids": [evidence.artifact_id],
                "polarity": "supports",
                "qualifier": "within the source",
                "scope": source_id,
            }
        )
    packet = EvidencePacketBuilder(
        EvidencePacketPolicy(
            token_budget=500,
            citation_budget=len(pairs),
            claim_budget=len(pairs),
            max_per_source=1,
            max_per_section=len(pairs),
        )
    ).build(
        question_artifact_id=_artifact("question"),
        scope_artifact_id=_artifact("scope"),
        retrieval_trace_artifact_ids=(_artifact("trace"),),
        candidates=tuple(evidence_items),
    )
    candidate = {
        "schema_version": "bijux.canon.reason.provider_synthesis_candidate.v1",
        "outcome": "answered",
        "answer": " ".join(claim for claim, _ in pairs),
        "claims": candidate_claims,
        "limitations": ["Admission policy is still required."],
        "conflicts": [],
        "assumptions": [],
    }
    provider = OpenAICompatibleStructuredSynthesizer(
        StructuredProviderConfiguration(
            base_url="http://127.0.0.1:8000", model="test-model"
        ),
        credential_resolver=lambda: "secret",
        transport=_Transport(candidate),
    )
    synthesis = provider.synthesize(question="Question?", evidence_packet=packet)
    claims = AtomicClaimNormalizer().normalize_provider(synthesis)
    citations = ClaimCitationLinker().link(
        claim_set=claims, evidence_packet=packet, sources=tuple(sources)
    )
    report = DeterministicCitationVerifier(
        policy=verification_policy,
        structured_verifier=verifier,
    ).verify(
        claim_set=claims,
        citation_set=citations,
        evidence_packet=packet,
        sources=tuple(sources),
    )
    return claims, citations, report


class _SemanticVerifier:
    def __init__(self, confidence: float) -> None:
        self._confidence = confidence

    def assess(
        self, *, claim: AtomicClaim, citation: ClaimCitationLink
    ) -> StructuredEntailmentDecision:
        return StructuredEntailmentDecision.create(
            verifier_id="reviewed-test-semantic-verifier",
            verifier_configuration_artifact_id=_artifact("semantic-config"),
            claim_artifact_id=claim.artifact_id,
            claim_citation_link_artifact_id=citation.artifact_id,
            verdict=EntailmentVerdict.direct_support,
            confidence=self._confidence,
            entity_alignment=True,
            scope_alignment=True,
            negation_alignment=True,
            qualifier_alignment=True,
            rationale_code="reviewed_semantic_support",
        )


def _empty_pipeline() -> tuple[
    NormalizedClaimSet, ClaimCitationSet, CitationVerificationReport
]:
    packet = EvidencePacketBuilder(
        EvidencePacketPolicy(
            token_budget=10,
            citation_budget=1,
            claim_budget=1,
            max_per_source=1,
            max_per_section=1,
        )
    ).build(
        question_artifact_id=_artifact("empty-question"),
        scope_artifact_id=_artifact("empty-scope"),
        retrieval_trace_artifact_ids=(_artifact("empty-trace"),),
        candidates=(),
    )
    synthesis = CredentialFreeSynthesizer().synthesize(
        question="Unknown?", evidence_packet=packet
    )
    claims = AtomicClaimNormalizer().normalize_credential_free(synthesis)
    citations = ClaimCitationLinker().link(
        claim_set=claims, evidence_packet=packet, sources=()
    )
    report = DeterministicCitationVerifier().verify(
        claim_set=claims,
        citation_set=citations,
        evidence_packet=packet,
        sources=(),
    )
    return claims, citations, report


def test_all_direct_support_is_admitted_with_only_exact_link_ids() -> None:
    claim = "Ancient DNA fragments were shorter."
    claims, citations, report = _pipeline(((claim, claim),))

    decision = GroundingAdmissionService().decide(
        claim_set=claims,
        citation_set=citations,
        verification_report=report,
    )

    assert decision.outcome is GroundingAdmissionOutcome.admitted
    assert decision.admitted_claim_artifact_ids == (claims.claims[0].artifact_id,)
    assert decision.admitted_citation_link_artifact_ids == (
        citations.links[0].artifact_id,
    )
    assert decision.rejected_claims == ()
    assert decision.evidence_gaps == ()


def test_mixed_verdicts_admit_only_supported_claim_and_citation() -> None:
    supported = "Ancient DNA fragments were shorter."
    unsupported = "Ocean temperatures increased globally."
    claims, citations, report = _pipeline(
        (
            (supported, supported),
            (unsupported, "Ancient samples retained fragmented DNA molecules."),
        )
    )
    assert tuple(item.verdict for item in report.claims) == (
        EntailmentVerdict.direct_support,
        EntailmentVerdict.irrelevance,
    )

    decision = GroundingAdmissionService().decide(
        claim_set=claims,
        citation_set=citations,
        verification_report=report,
    )

    assert decision.outcome is GroundingAdmissionOutcome.partially_admitted
    assert decision.admitted_claim_artifact_ids == (claims.claims[0].artifact_id,)
    assert decision.admitted_citation_link_artifact_ids == (
        citations.links[0].artifact_id,
    )
    assert decision.rejected_claims[0].claim_artifact_id == claims.claims[1].artifact_id
    assert decision.evidence_gaps[0].code is EvidenceGapCode.irrelevant_evidence


def test_unsupported_claim_abstains_without_invented_citation() -> None:
    claims, citations, report = _pipeline(
        (("Ocean temperatures increased globally.", "Ancient DNA degraded rapidly."),)
    )

    decision = GroundingAdmissionService().decide(
        claim_set=claims,
        citation_set=citations,
        verification_report=report,
    )

    assert decision.outcome is GroundingAdmissionOutcome.abstained
    assert decision.admitted_claim_artifact_ids == ()
    assert decision.admitted_citation_link_artifact_ids == ()
    assert {gap.code for gap in decision.evidence_gaps} == {
        EvidenceGapCode.irrelevant_evidence,
        EvidenceGapCode.support_coverage_below_policy,
    }


def test_no_claims_abstains_with_actionable_retrieval_gap() -> None:
    claims, citations, report = _empty_pipeline()

    decision = GroundingAdmissionService().decide(
        claim_set=claims,
        citation_set=citations,
        verification_report=report,
    )

    assert decision.outcome is GroundingAdmissionOutcome.abstained
    assert decision.evidence_gaps[0].code is EvidenceGapCode.no_retrieved_evidence
    assert decision.evidence_gaps[0].required_action


@pytest.mark.parametrize(
    ("retrieval_status", "vex_status", "unsafe", "budget", "gap_code"),
    [
        (
            RetrievalEvidenceStatus.insufficient,
            VexEvidenceStatus.not_applicable,
            False,
            False,
            EvidenceGapCode.no_retrieved_evidence,
        ),
        (
            RetrievalEvidenceStatus.refused,
            VexEvidenceStatus.not_applicable,
            False,
            False,
            EvidenceGapCode.retrieval_refused,
        ),
        (
            RetrievalEvidenceStatus.failed,
            VexEvidenceStatus.not_applicable,
            False,
            False,
            EvidenceGapCode.retrieval_failed,
        ),
        (
            RetrievalEvidenceStatus.refused,
            VexEvidenceStatus.below_policy,
            False,
            False,
            EvidenceGapCode.unsafe_or_unverified_evidence,
        ),
        (
            RetrievalEvidenceStatus.refused,
            VexEvidenceStatus.not_applicable,
            False,
            True,
            EvidenceGapCode.policy_or_budget_refusal,
        ),
        (
            RetrievalEvidenceStatus.success,
            VexEvidenceStatus.verified,
            True,
            False,
            EvidenceGapCode.unsafe_or_unverified_evidence,
        ),
    ],
)
def test_upstream_evidence_state_overrides_apparently_supported_claims(
    retrieval_status: RetrievalEvidenceStatus,
    vex_status: VexEvidenceStatus,
    unsafe: bool,
    budget: bool,
    gap_code: EvidenceGapCode,
) -> None:
    claim = "Ancient DNA fragments were shorter."
    claims, citations, report = _pipeline(((claim, claim),))
    usable = retrieval_status is RetrievalEvidenceStatus.success
    state = GroundingEvidenceState.create(
        retrieval_status=retrieval_status,
        vex_status=vex_status,
        retrieved_evidence_count=1 if usable else 0,
        selected_evidence_count=1 if usable else 0,
        packet_completeness=(
            PacketCompleteness.complete if usable else PacketCompleteness.insufficient
        ),
        unsafe_or_unverified=unsafe,
        budget_exhausted=budget,
        policy_detail="Typed upstream evidence condition.",
        remediation="Apply the typed remediation.",
    )

    decision = GroundingAdmissionService().decide(
        claim_set=claims,
        citation_set=citations,
        verification_report=report,
        evidence_state=state,
    )

    assert decision.outcome is GroundingAdmissionOutcome.abstained
    assert decision.admitted_claim_artifact_ids == ()
    assert decision.admitted_citation_link_artifact_ids == ()
    assert decision.evidence_state_artifact_id == state.artifact_id
    assert decision.evidence_gaps[0].code is gap_code


@pytest.mark.parametrize(
    ("status", "gap_code"),
    [
        (GroundingRequestStatus.fabricated_entity, EvidenceGapCode.fabricated_entity),
        (GroundingRequestStatus.out_of_scope, EvidenceGapCode.out_of_scope),
    ],
)
def test_request_exclusion_overrides_support_and_removes_citations(
    status: GroundingRequestStatus, gap_code: EvidenceGapCode
) -> None:
    claim = "Ancient DNA fragments were shorter."
    claims, citations, report = _pipeline(((claim, claim),))

    decision = GroundingAdmissionService().decide(
        claim_set=claims,
        citation_set=citations,
        verification_report=report,
        request_status=status,
    )

    assert decision.outcome is GroundingAdmissionOutcome.abstained
    assert not decision.admitted_citation_link_artifact_ids
    assert decision.evidence_gaps[0].code is gap_code


def test_corrupt_evidence_abstains_without_verification_or_citations() -> None:
    claim = "Ancient DNA fragments were shorter."
    claims, citations, _ = _pipeline(((claim, claim),))

    decision = GroundingAdmissionService().decide(
        claim_set=claims,
        citation_set=citations,
        verification_report=None,
        request_status=GroundingRequestStatus.corrupt_evidence,
    )

    assert decision.outcome is GroundingAdmissionOutcome.abstained
    assert decision.verification_report_artifact_id is None
    assert decision.admitted_citation_link_artifact_ids == ()
    assert decision.evidence_gaps[0].code is EvidenceGapCode.integrity_failure


def test_stricter_policy_abstains_on_partial_support() -> None:
    supported = "Ancient DNA fragments were shorter."
    claims, citations, report = _pipeline(
        (
            (supported, supported),
            ("Ocean temperatures increased globally.", "Ancient DNA degraded."),
        )
    )
    service = GroundingAdmissionService(
        CalibratedAbstentionPolicy(minimum_supported_fraction=0.75)
    )

    decision = service.decide(
        claim_set=claims,
        citation_set=citations,
        verification_report=report,
    )

    assert decision.outcome is GroundingAdmissionOutcome.abstained
    assert not decision.admitted_claim_artifact_ids
    assert not decision.admitted_citation_link_artifact_ids


def test_material_opposition_forces_unresolved_conflict_abstention() -> None:
    supported = "Ancient DNA fragments were shorter."
    opposed = "Ancient DNA fragments were not shorter."
    claims, citations, report = _pipeline(
        ((supported, supported), (opposed, supported))
    )
    assert EntailmentVerdict.opposition in {item.verdict for item in report.claims}

    decision = GroundingAdmissionService().decide(
        claim_set=claims,
        citation_set=citations,
        verification_report=report,
    )

    assert decision.outcome is GroundingAdmissionOutcome.abstained
    assert decision.unresolved_opposition_claims == 1
    assert EvidenceGapCode.unresolved_conflict in {
        item.code for item in decision.evidence_gaps
    }
    assert decision.admitted_claim_artifact_ids == ()


def test_semantic_support_below_admission_confidence_abstains() -> None:
    claims, citations, report = _pipeline(
        (
            (
                "DNA preservation declined in the sampled tissue.",
                "Genetic material became less recoverable in the sampled tissue.",
            ),
        ),
        verifier=_SemanticVerifier(0.85),
        verification_policy=CitationVerificationPolicy(
            structured_minimum_confidence=0.8
        ),
    )
    assert report.claims[0].verdict is EntailmentVerdict.direct_support

    decision = GroundingAdmissionService().decide(
        claim_set=claims,
        citation_set=citations,
        verification_report=report,
    )

    assert decision.outcome is GroundingAdmissionOutcome.abstained
    assert decision.minimum_support_confidence == 0.85
    assert decision.evidence_gaps[-1].code is (
        EvidenceGapCode.support_coverage_below_policy
    )


def test_verification_report_for_other_inputs_is_rejected() -> None:
    first = _pipeline((("First stable claim.", "First stable claim."),))
    second = _pipeline((("Second stable claim.", "Second stable claim."),))

    with pytest.raises(ValueError, match="does not belong"):
        GroundingAdmissionService().decide(
            claim_set=first[0],
            citation_set=first[1],
            verification_report=second[2],
        )


def test_admission_decision_is_restart_safe_and_rejects_identity_drift() -> None:
    claim = "Ancient DNA fragments were shorter."
    claims, citations, report = _pipeline(((claim, claim),))
    decision = GroundingAdmissionService().decide(
        claim_set=claims,
        citation_set=citations,
        verification_report=report,
    )
    restarted = GroundingAdmissionDecision.model_validate_json(
        decision.model_dump_json()
    )
    drifted = decision.model_dump(mode="json")
    drifted["artifact_id"] = _artifact("different")

    assert restarted == decision
    with pytest.raises(ValidationError, match="identity"):
        GroundingAdmissionDecision.model_validate(drifted)
