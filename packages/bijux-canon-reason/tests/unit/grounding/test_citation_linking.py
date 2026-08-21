# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Exact atomic-claim citation-linking tests."""

from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError

from bijux_canon_reason.grounding import (
    AtomicClaimNormalizer,
    CitationEvidence,
    CitationLinkingError,
    CitationLinkingErrorCode,
    CitationSourceDescriptor,
    ClaimCitationLinker,
    ClaimCitationRole,
    ClaimCitationSet,
    CredentialFreeSynthesizer,
    EvidencePacketBuilder,
    EvidencePacketPolicy,
    ImmutableEvidenceLocator,
    JsonHttpResponse,
    OpenAICompatibleStructuredSynthesizer,
    StructuredProviderConfiguration,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _artifact(value: str) -> str:
    return f"sha256:{_sha(value)}"


def _packet(*, empty: bool = False):
    exact_text = "Ancient DNA fragments were shorter than the source controls."
    source_content = "Complete immutable source content."
    evidence = CitationEvidence(
        artifact_id=_artifact("evidence"),
        chunk_artifact_id=_artifact("chunk"),
        retrieval_artifact_id=_artifact("retrieval"),
        document_id="document",
        source_id="source",
        section_path=("results", "fragmentation"),
        locator=ImmutableEvidenceLocator(
            artifact_id=_artifact("locator"),
            source_artifact_id=_artifact("source"),
            source_uri="https://doi.org/10.1000/source",
            source_content_sha256=_sha(source_content),
            scheme="unicode-code-point",
            selectors=(("char_start", 10), ("char_end", 72)),
        ),
        exact_text=exact_text,
        exact_text_sha256=_sha(exact_text),
        rank=1,
        relevance_score=1.0,
        claim_keys=("claim",),
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
        question_artifact_id=_artifact("question"),
        scope_artifact_id=_artifact("scope"),
        retrieval_trace_artifact_ids=(_artifact("trace"),),
        candidates=() if empty else (evidence,),
    )
    source = CitationSourceDescriptor.create(
        source_id="source",
        title="A durable source title",
        canonical_uri=evidence.locator.source_uri,
        doi="10.1000/source",
        source_content_sha256=evidence.locator.source_content_sha256,
    )
    return packet, evidence, source


class _Transport:
    def __init__(self, candidate: dict[str, object]) -> None:
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


def _provider_claims(polarity: str = "supports"):
    packet, evidence, source = _packet()
    statement = "The admitted study reports shorter ancient DNA fragments."
    candidate = {
        "schema_version": "bijux.canon.reason.provider_synthesis_candidate.v1",
        "outcome": "answered",
        "answer": statement,
        "claims": [
            {
                "statement": statement,
                "citation_evidence_artifact_ids": [evidence.artifact_id],
                "polarity": polarity,
                "qualifier": "within the admitted study",
                "scope": "the source samples",
            }
        ],
        "limitations": ["The provider relationship remains unverified."],
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
    return claims, packet, evidence, source


def test_extractive_claim_links_complete_exact_source_evidence() -> None:
    packet, evidence, source = _packet()
    synthesis = CredentialFreeSynthesizer().synthesize(
        question="What happened?", evidence_packet=packet
    )
    claims = AtomicClaimNormalizer().normalize_credential_free(synthesis)

    result = ClaimCitationLinker().link(
        claim_set=claims, evidence_packet=packet, sources=(source,)
    )
    restarted = ClaimCitationSet.model_validate_json(result.model_dump_json())

    assert restarted == result
    assert result.claim_artifact_ids == (claims.claims[0].artifact_id,)
    link = result.links[0]
    assert link.role is ClaimCitationRole.source_observation
    assert link.source_title == source.title
    assert link.source_doi == source.doi
    assert link.source_uri == source.canonical_uri
    assert link.locator_selectors == evidence.locator.selectors
    assert link.exact_text == evidence.exact_text
    assert link.exact_text_sha256 == _sha(link.exact_text)


@pytest.mark.parametrize(
    ("polarity", "role"),
    [
        ("supports", ClaimCitationRole.proposed_support),
        ("opposes", ClaimCitationRole.proposed_opposition),
        ("ambiguous", ClaimCitationRole.proposed_ambiguity),
    ],
)
def test_provider_polarity_maps_to_unverified_citation_role(
    polarity: str, role: ClaimCitationRole
) -> None:
    claims, packet, _, source = _provider_claims(polarity)

    result = ClaimCitationLinker().link(
        claim_set=claims, evidence_packet=packet, sources=(source,)
    )

    assert result.links[0].role is role


def test_empty_claim_set_has_honest_empty_citation_set() -> None:
    packet, _, _ = _packet(empty=True)
    synthesis = CredentialFreeSynthesizer().synthesize(
        question="Unknown?", evidence_packet=packet
    )
    claims = AtomicClaimNormalizer().normalize_credential_free(synthesis)

    result = ClaimCitationLinker().link(
        claim_set=claims, evidence_packet=packet, sources=()
    )

    assert result.claim_artifact_ids == ()
    assert result.links == ()


def test_claim_citation_absent_from_packet_fails_closed() -> None:
    claims, _, _, source = _provider_claims()
    empty_packet, _, _ = _packet(empty=True)

    with pytest.raises(CitationLinkingError) as caught:
        ClaimCitationLinker().link(
            claim_set=claims, evidence_packet=empty_packet, sources=(source,)
        )

    assert caught.value.code is CitationLinkingErrorCode.citation_missing


def test_missing_source_metadata_fails_closed() -> None:
    claims, packet, _, _ = _provider_claims()

    with pytest.raises(CitationLinkingError) as caught:
        ClaimCitationLinker().link(claim_set=claims, evidence_packet=packet, sources=())

    assert caught.value.code is CitationLinkingErrorCode.source_metadata_missing


def test_duplicate_source_metadata_fails_closed() -> None:
    claims, packet, _, source = _provider_claims()

    with pytest.raises(CitationLinkingError) as caught:
        ClaimCitationLinker().link(
            claim_set=claims, evidence_packet=packet, sources=(source, source)
        )

    assert caught.value.code is CitationLinkingErrorCode.source_metadata_collision


def test_source_metadata_locator_disagreement_fails_closed() -> None:
    claims, packet, _, source = _provider_claims()
    mismatched = CitationSourceDescriptor.create(
        source_id=source.source_id,
        title=source.title,
        canonical_uri="https://doi.org/10.1000/different",
        doi="10.1000/different",
        source_content_sha256=source.source_content_sha256,
    )

    with pytest.raises(CitationLinkingError) as caught:
        ClaimCitationLinker().link(
            claim_set=claims, evidence_packet=packet, sources=(mismatched,)
        )

    assert caught.value.code is CitationLinkingErrorCode.source_identity_mismatch


def test_claim_citation_set_rejects_identity_drift() -> None:
    claims, packet, _, source = _provider_claims()
    result = ClaimCitationLinker().link(
        claim_set=claims, evidence_packet=packet, sources=(source,)
    )
    drifted = result.model_dump(mode="json")
    drifted["artifact_id"] = _artifact("different")

    with pytest.raises(ValidationError, match="identity"):
        ClaimCitationSet.model_validate(drifted)
