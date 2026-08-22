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
    ClaimCitationSet,
    CredentialFreeSynthesizer,
    DeterministicCitationVerifier,
    EntailmentVerdict,
    EvidencePacketBuilder,
    EvidencePacketPolicy,
    ImmutableEvidenceLocator,
    JsonHttpResponse,
    NormalizedClaimSet,
    OpenAICompatibleStructuredSynthesizer,
    StructuredProviderConfiguration,
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
) -> tuple[CitationVerificationReport, NormalizedClaimSet, ClaimCitationSet]:
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
    report = DeterministicCitationVerifier().verify(
        claim_set=claims, citation_set=citations
    )
    return report, claims, citations


def test_exact_evidence_span_is_direct_support_with_complete_integrity() -> None:
    claim = "Ancient DNA fragments were shorter."
    report, _, _ = _verification(
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


def test_high_overlap_with_opposite_negation_requires_semantic_verification() -> None:
    report, _, _ = _verification(
        "The control did change.", "The control did not change."
    )

    assert report.claims[0].verdict is EntailmentVerdict.insufficiency
    assert report.claims[0].assessments[0].rationale_code == (
        "semantic_entailment_not_deterministically_established"
    )


def test_related_nonexact_evidence_requires_semantic_verification() -> None:
    report, _, _ = _verification(
        "Ancient DNA fragments were shorter.",
        "Ancient DNA fragments may have been shorter in a subset.",
    )

    assert report.claims[0].verdict is EntailmentVerdict.insufficiency


def test_unrelated_citation_is_not_given_an_overlap_only_verdict() -> None:
    report, _, _ = _verification(
        "Ocean temperatures increased globally.",
        "Ancient DNA fragments degraded in the tested samples.",
    )

    assert report.claims[0].verdict is EntailmentVerdict.insufficiency


def test_too_little_evidence_is_insufficient_even_when_present() -> None:
    report, _, _ = _verification("Tiny result.", "Tiny.")

    assert report.claims[0].verdict is EntailmentVerdict.insufficiency


def test_provider_proposed_role_does_not_decide_entailment() -> None:
    claim = "The control changed."
    report, _, _ = _verification(claim, claim, polarity="opposes")

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
        claim_set=claims, citation_set=citations
    )

    assert report.outcome is CitationVerificationOutcome.no_claims
    assert report.integrity_total_links == 0
    assert report.claims == ()


def test_citation_set_for_another_claim_set_fails_closed() -> None:
    _, claims, _ = _verification("First claim.", "First claim in evidence.")
    _, _, other_citations = _verification("Second claim.", "Second claim in evidence.")

    with pytest.raises(CitationVerificationError) as caught:
        DeterministicCitationVerifier().verify(
            claim_set=claims, citation_set=other_citations
        )

    assert caught.value.code is CitationVerificationErrorCode.claim_set_mismatch


def test_unreachable_locator_fails_integrity_gate() -> None:
    _, claims, citations = _verification(
        "A located claim.", "A located claim in exact evidence."
    )
    unreachable = citations.links[0].model_copy(
        update={"locator_selectors": (("unrecognized", 1),)}
    )
    drifted_citations = citations.model_copy(update={"links": (unreachable,)})

    with pytest.raises(CitationVerificationError) as caught:
        DeterministicCitationVerifier().verify(
            claim_set=claims, citation_set=drifted_citations
        )

    assert caught.value.code is CitationVerificationErrorCode.integrity_failure


def test_verification_report_rejects_identity_drift() -> None:
    report, _, _ = _verification("A stable claim.", "A stable claim.")
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
