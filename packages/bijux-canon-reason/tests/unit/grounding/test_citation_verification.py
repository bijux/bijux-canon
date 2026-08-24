# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Deterministic citation-integrity and entailment tests."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json

from pydantic import ValidationError
import pytest

from bijux_canon_reason.grounding import (
    AtomicClaim,
    AtomicClaimNormalizer,
    CitationEvidence,
    CitationIntegrityStatus,
    CitationSourceDescriptor,
    CitationVerificationError,
    CitationVerificationErrorCode,
    CitationVerificationOutcome,
    CitationVerificationPolicy,
    CitationVerificationReport,
    ClaimCitationLinker,
    ClaimCitationLink,
    ClaimCitationSet,
    CredentialFreeSynthesizer,
    DeterministicCitationVerifier,
    EntailmentVerdict,
    EvidencePacket,
    EvidencePacketBuilder,
    EvidencePacketPolicy,
    ImmutableEvidenceLocator,
    JsonHttpResponse,
    NormalizedClaimSet,
    OpenAICompatibleStructuredSynthesizer,
    StructuredProviderConfiguration,
    StructuredEntailmentDecision,
    StructuredEntailmentVerifier,
)


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


def _verification(
    claim_text: str,
    evidence_text: str,
    *,
    polarity: str = "supports",
    structured_verifier: StructuredEntailmentVerifier | None = None,
) -> tuple[
    CitationVerificationReport,
    NormalizedClaimSet,
    ClaimCitationSet,
    EvidencePacket,
    tuple[CitationSourceDescriptor, ...],
]:
    source_content = f"Immutable source containing: {evidence_text}"
    evidence = CitationEvidence(
        artifact_id=_artifact(f"evidence:{evidence_text}"),
        chunk_artifact_id=_artifact(f"chunk:{evidence_text}"),
        retrieval_artifact_id=_artifact("retrieval"),
        document_id="document",
        source_id="source",
        section_path=("results",),
        locator=ImmutableEvidenceLocator(
            artifact_id=_artifact(f"locator:{evidence_text}"),
            source_artifact_id=_artifact(source_content),
            source_uri="https://doi.org/10.1000/source",
            source_content_sha256=_sha(source_content),
            scheme="unicode-code-point",
            selectors=(("char_start", 29), ("char_end", 29 + len(evidence_text))),
        ),
        exact_text=evidence_text,
        exact_text_sha256=_sha(evidence_text),
        rank=1,
        relevance_score=1.0,
    )
    packet = EvidencePacketBuilder(
        EvidencePacketPolicy(
            token_budget=100,
            citation_budget=1,
            claim_budget=1,
            max_per_source=1,
            max_per_section=1,
        )
    ).build(
        question_artifact_id=_artifact(f"question:{claim_text}"),
        scope_artifact_id=_artifact("scope"),
        retrieval_trace_artifact_ids=(_artifact("trace"),),
        candidates=(evidence,),
    )
    candidate = {
        "schema_version": "bijux.canon.reason.provider_synthesis_candidate.v1",
        "outcome": "answered",
        "answer": claim_text,
        "claims": [
            {
                "statement": claim_text,
                "citation_evidence_artifact_ids": [evidence.artifact_id],
                "polarity": polarity,
                "qualifier": "within the source",
                "scope": "the source study",
            }
        ],
        "limitations": ["Deterministic verification is still required."],
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
    source = CitationSourceDescriptor.create(
        source_id="source",
        title="A durable source title",
        canonical_uri=evidence.locator.source_uri,
        doi="10.1000/source",
        source_content_sha256=evidence.locator.source_content_sha256,
    )
    citations = ClaimCitationLinker().link(
        claim_set=claims, evidence_packet=packet, sources=(source,)
    )
    report = DeterministicCitationVerifier(
        structured_verifier=structured_verifier
    ).verify(
        claim_set=claims,
        citation_set=citations,
        evidence_packet=packet,
        sources=(source,),
    )
    return report, claims, citations, packet, (source,)


class _SemanticVerifier:
    def __init__(
        self,
        *,
        verdict: EntailmentVerdict,
        confidence: float = 0.99,
        entity_alignment: bool = True,
        scope_alignment: bool = True,
        negation_alignment: bool = True,
        qualifier_alignment: bool = True,
        wrong_claim: bool = False,
    ) -> None:
        self.verdict = verdict
        self.confidence = confidence
        self.entity_alignment = entity_alignment
        self.scope_alignment = scope_alignment
        self.negation_alignment = negation_alignment
        self.qualifier_alignment = qualifier_alignment
        self.wrong_claim = wrong_claim

    def assess(
        self, *, claim: AtomicClaim, citation: ClaimCitationLink
    ) -> StructuredEntailmentDecision:
        return StructuredEntailmentDecision.create(
            verifier_id="deterministic-test-semantic-verifier",
            verifier_configuration_artifact_id=_artifact("semantic-config"),
            claim_artifact_id=(
                _artifact("wrong-claim") if self.wrong_claim else claim.artifact_id
            ),
            claim_citation_link_artifact_id=citation.artifact_id,
            verdict=self.verdict,
            confidence=self.confidence,
            entity_alignment=self.entity_alignment,
            scope_alignment=self.scope_alignment,
            negation_alignment=self.negation_alignment,
            qualifier_alignment=self.qualifier_alignment,
            rationale_code="reviewed_semantic_relation",
        )


def test_exact_evidence_span_is_direct_support_with_complete_integrity() -> None:
    claim = "Ancient DNA fragments were shorter."
    report, _, _, _, _ = _verification(
        claim, f"The study reports the following result: {claim}"
    )
    restarted = CitationVerificationReport.model_validate_json(report.model_dump_json())

    assert restarted == report
    assert report.outcome is CitationVerificationOutcome.claims_verified
    assert report.integrity_verified_links == report.integrity_total_links == 1
    assert report.claims[0].verdict is EntailmentVerdict.direct_support
    assessment = report.claims[0].assessments[0]
    assert assessment.integrity is CitationIntegrityStatus.verified
    assert assessment.exact_claim_span is True


def test_exact_claim_words_inside_negated_evidence_are_opposition() -> None:
    claim = "The control changed."
    report, _, _, _, _ = _verification(
        claim,
        f"The study denied the following assertion: {claim}",
    )

    assessment = report.claims[0].assessments[0]
    assert assessment.exact_claim_span is True
    assert report.claims[0].verdict is EntailmentVerdict.opposition
    assert assessment.rationale_code == "exact_claim_span_has_opposite_negation"


def test_exact_claim_under_possible_negation_remains_ambiguous() -> None:
    claim = "The control changed."
    report, _, _, _, _ = _verification(
        claim,
        f"It may not be true that {claim}",
    )

    assert report.claims[0].verdict is EntailmentVerdict.ambiguity
    assert report.claims[0].assessments[0].rationale_code == (
        "exact_span_opposite_negation_below_claim_modality"
    )


def test_aligned_proposition_with_opposite_negation_is_opposition() -> None:
    report, _, _, _, _ = _verification(
        "The control did change.", "The control did not change."
    )

    assert report.claims[0].verdict is EntailmentVerdict.opposition
    assert report.claims[0].assessments[0].rationale_code == (
        "aligned_proposition_has_opposite_negation"
    )


def test_possible_opposite_evidence_does_not_overstate_opposition() -> None:
    report, _, _, _, _ = _verification(
        "The control changed.", "The control may not have changed."
    )

    assert report.claims[0].verdict is EntailmentVerdict.ambiguity


def test_weaker_modality_and_narrower_scope_remain_ambiguous() -> None:
    report, _, _, _, _ = _verification(
        "Ancient DNA fragments were shorter.",
        "Ancient DNA fragments may have been shorter in a subset.",
    )

    assert report.claims[0].verdict is EntailmentVerdict.ambiguity


def test_reproducible_conservative_projection_is_direct_support() -> None:
    report, _, _, _, _ = _verification(
        "Yields can remain below 1% in hot regions.",
        "Our results show that yields can remain below 1% in hot regions.",
    )

    assessment = report.claims[0].assessments[0]
    assert report.claims[0].verdict is EntailmentVerdict.direct_support
    assert assessment.exact_claim_span is False
    assert assessment.rationale_code == "claim_is_verified_conservative_projection"


def test_projection_does_not_accept_an_entity_or_number_swap() -> None:
    report, _, _, _, _ = _verification(
        "Part B yields can remain below 2% in hot regions.",
        "Our results show that part C yields can remain below 1% in hot regions.",
    )

    assert report.claims[0].verdict is EntailmentVerdict.ambiguity


def test_unrelated_citation_is_not_given_an_overlap_only_verdict() -> None:
    report, _, _, _, _ = _verification(
        "Ocean temperatures increased globally.",
        "Ancient DNA fragments degraded in the tested samples.",
    )

    assert report.claims[0].verdict is EntailmentVerdict.irrelevance


def test_nonexact_ordered_claim_with_matching_qualifiers_is_direct_support() -> None:
    report, _, _, _, _ = _verification(
        "The control changed by 12% in tested samples.",
        "In the experiment, the control changed by 12% in tested samples.",
    )

    assessment = report.claims[0].assessments[0]
    assert report.claims[0].verdict is EntailmentVerdict.direct_support
    assert assessment.rationale_code == "conservative_lexical_semantic_alignment"


def test_reversed_entity_relation_is_not_supported_by_term_overlap() -> None:
    report, _, _, _, _ = _verification(
        "Part B exceeded part C.",
        "Part C exceeded part B.",
    )

    assert report.claims[0].verdict is EntailmentVerdict.ambiguity


def test_unmatched_population_boundary_is_not_supported() -> None:
    report, _, _, _, _ = _verification(
        "DNA recovery remained high.",
        "DNA recovery remained high in only some tested samples.",
    )

    assert report.claims[0].verdict is EntailmentVerdict.ambiguity


def test_unmatched_numeric_qualifier_is_not_supported() -> None:
    report, _, _, _, _ = _verification(
        "Endogenous yield exceeded 12%.",
        "Endogenous yield exceeded 2%.",
    )

    assert report.claims[0].verdict is EntailmentVerdict.ambiguity


def test_optional_structured_verifier_can_admit_aligned_paraphrase() -> None:
    verifier = _SemanticVerifier(verdict=EntailmentVerdict.direct_support)
    report, _, _, _, _ = _verification(
        "DNA preservation declined in the sampled tissue.",
        "Genetic material became less recoverable in the sampled tissue.",
        structured_verifier=verifier,
    )

    assessment = report.claims[0].assessments[0]
    restarted = CitationVerificationReport.model_validate_json(report.model_dump_json())
    assert report.claims[0].verdict is EntailmentVerdict.direct_support
    assert assessment.structured_decision is not None
    assert assessment.structured_decision.verdict is EntailmentVerdict.direct_support
    assert (
        restarted.claims[0].assessments[0].structured_decision
        == assessment.structured_decision
    )


@pytest.mark.parametrize(
    "verifier",
    (
        _SemanticVerifier(
            verdict=EntailmentVerdict.direct_support,
            confidence=0.7,
        ),
        _SemanticVerifier(
            verdict=EntailmentVerdict.direct_support,
            scope_alignment=False,
        ),
        _SemanticVerifier(
            verdict=EntailmentVerdict.direct_support,
            qualifier_alignment=False,
        ),
        _SemanticVerifier(
            verdict=EntailmentVerdict.direct_support,
            negation_alignment=False,
        ),
    ),
)
def test_structured_support_requires_confidence_and_all_alignment(
    verifier: _SemanticVerifier,
) -> None:
    report, _, _, _, _ = _verification(
        "DNA preservation declined.",
        "Genetic material became less recoverable.",
        structured_verifier=verifier,
    )

    assert report.claims[0].verdict is EntailmentVerdict.ambiguity
    assert report.claims[0].assessments[0].structured_decision is not None


def test_structured_opposition_requires_explicit_negation_misalignment() -> None:
    verifier = _SemanticVerifier(
        verdict=EntailmentVerdict.opposition,
        negation_alignment=False,
    )
    report, _, _, _, _ = _verification(
        "The control changed.",
        "The control remained stable.",
        structured_verifier=verifier,
    )

    assert report.claims[0].verdict is EntailmentVerdict.opposition


def test_structured_decision_for_other_inputs_fails_closed() -> None:
    verifier = _SemanticVerifier(
        verdict=EntailmentVerdict.direct_support,
        wrong_claim=True,
    )

    with pytest.raises(CitationVerificationError) as caught:
        _verification(
            "DNA preservation declined.",
            "Genetic material became less recoverable.",
            structured_verifier=verifier,
        )

    assert (
        caught.value.code is CitationVerificationErrorCode.structured_decision_invalid
    )


def test_too_little_evidence_is_insufficient_even_when_present() -> None:
    report, _, _, _, _ = _verification("Tiny result.", "Tiny.")

    assert report.claims[0].verdict is EntailmentVerdict.insufficiency


def test_provider_proposed_role_does_not_decide_entailment() -> None:
    claim = "The control changed."
    report, _, _, _, _ = _verification(claim, claim, polarity="opposes")

    assert report.claims[0].verdict is EntailmentVerdict.direct_support


def test_empty_claims_produce_honest_no_claims_report() -> None:
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

    assert report.outcome is CitationVerificationOutcome.no_claims
    assert report.integrity_total_links == 0
    assert report.claims == ()


def test_citation_set_for_another_claim_set_fails_closed() -> None:
    _, claims, _, packet, sources = _verification(
        "First claim.", "First claim in evidence."
    )
    _, _, other_citations, _, _ = _verification(
        "Second claim.", "Second claim in evidence."
    )

    with pytest.raises(CitationVerificationError) as caught:
        DeterministicCitationVerifier().verify(
            claim_set=claims,
            citation_set=other_citations,
            evidence_packet=packet,
            sources=sources,
        )

    assert caught.value.code is CitationVerificationErrorCode.claim_set_mismatch


def test_unreachable_locator_fails_integrity_gate() -> None:
    _, claims, citations, packet, sources = _verification(
        "A located claim.", "A located claim in exact evidence."
    )
    unreachable = citations.links[0].model_copy(
        update={"locator_selectors": (("unrecognized", 1),)}
    )
    drifted_citations = citations.model_copy(update={"links": (unreachable,)})

    with pytest.raises(CitationVerificationError) as caught:
        DeterministicCitationVerifier().verify(
            claim_set=claims,
            citation_set=drifted_citations,
            evidence_packet=packet,
            sources=sources,
        )

    assert caught.value.code is CitationVerificationErrorCode.evidence_identity_mismatch


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("document_id", "invented-document"),
        ("chunk_artifact_id", _artifact("invented-chunk")),
        ("retrieval_artifact_id", _artifact("stale-retrieval")),
        ("exact_text", "Invented quotation."),
        ("exact_text_sha256", _sha("Invented quotation.")),
    ),
)
def test_citation_evidence_authority_rejects_invented_or_stale_coordinates(
    field: str, value: str
) -> None:
    _, claims, citations, packet, sources = _verification(
        "A located claim.", "A located claim in exact evidence."
    )
    drifted_link = citations.links[0].model_copy(update={field: value})
    drifted_citations = citations.model_copy(update={"links": (drifted_link,)})

    with pytest.raises(CitationVerificationError) as caught:
        DeterministicCitationVerifier().verify(
            claim_set=claims,
            citation_set=drifted_citations,
            evidence_packet=packet,
            sources=sources,
        )

    assert caught.value.code is CitationVerificationErrorCode.evidence_identity_mismatch


def test_citation_source_authority_rejects_bibliographic_drift() -> None:
    _, claims, citations, packet, sources = _verification(
        "A located claim.", "A located claim in exact evidence."
    )
    source = sources[0]
    drifted_source = CitationSourceDescriptor.create(
        source_id=source.source_id,
        title="Invented title",
        canonical_uri=source.canonical_uri,
        doi=source.doi,
        source_content_sha256=source.source_content_sha256,
    )

    with pytest.raises(CitationVerificationError) as caught:
        DeterministicCitationVerifier().verify(
            claim_set=claims,
            citation_set=citations,
            evidence_packet=packet,
            sources=(drifted_source,),
        )

    assert caught.value.code is CitationVerificationErrorCode.source_identity_mismatch


def test_verification_report_rejects_identity_drift() -> None:
    report, _, _, _, _ = _verification("A stable claim.", "A stable claim.")
    drifted = report.model_dump(mode="json")
    drifted["artifact_id"] = _artifact("different")

    with pytest.raises(ValidationError, match="identity"):
        CitationVerificationReport.model_validate(drifted)


def test_policy_rejects_opposition_threshold_weaker_than_related_threshold() -> None:
    with pytest.raises(ValidationError, match="opposition coverage"):
        CitationVerificationPolicy(
            related_claim_term_coverage=0.8,
            opposition_claim_term_coverage=0.5,
        )
